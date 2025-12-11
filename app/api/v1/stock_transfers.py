from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferResponse,
    StockTransferItemResponse
)

router = APIRouter()


def generate_transfer_number(organization_id: str, db: Session) -> str:
    """Generate unique stock transfer number"""
    today = date.today()
    prefix = f"ST-{today.strftime('%Y%m%d')}"
    
    count = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM stock_transfers
            WHERE organization_id = :org_id
            AND DATE(created_at) = :today
        """),
        {"org_id": organization_id, "today": today}
    ).fetchone().count
    
    return f"{prefix}-{count + 1:04d}"


@router.get("/", response_model=List[StockTransferResponse])
def get_all_stock_transfers(
    status: Optional[str] = Query(None, description="Filter by status"),
    from_outlet_id: Optional[UUID] = Query(None, description="Filter by source outlet"),
    to_outlet_id: Optional[UUID] = Query(None, description="Filter by destination outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all stock transfers"""
    
    query = """
        SELECT 
            st.id, st.organization_id, st.transfer_no, st.from_outlet_id, st.to_outlet_id,
            st.stock_request_id, st.status, st.shipped_at, st.received_at,
            st.created_by, st.received_by, st.notes, st.created_at,
            o1.name as from_outlet_name,
            o2.name as to_outlet_name,
            u1.name as created_by_name
        FROM stock_transfers st
        JOIN outlets o1 ON o1.id = st.from_outlet_id
        JOIN outlets o2 ON o2.id = st.to_outlet_id
        JOIN users u1 ON u1.id = st.created_by
        WHERE st.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if status:
        query += " AND st.status = :status"
        params["status"] = status
    
    if from_outlet_id:
        query += " AND st.from_outlet_id = :from_outlet_id"
        params["from_outlet_id"] = str(from_outlet_id)
    
    if to_outlet_id:
        query += " AND st.to_outlet_id = :to_outlet_id"
        params["to_outlet_id"] = str(to_outlet_id)
    
    query += " ORDER BY st.created_at DESC"
    
    results = db.execute(text(query), params).fetchall()
    
    # Get items
    transfers = []
    for r in results:
        items = db.execute(
            text("""
                SELECT 
                    sti.id, sti.stock_transfer_id, sti.ingredient_id,
                    sti.qty, sti.unit_id, sti.unit_cost, sti.total_cost,
                    i.name as ingredient_name,
                    u.symbol as unit_symbol
                FROM stock_transfer_items sti
                JOIN ingredients i ON i.id = sti.ingredient_id
                JOIN units u ON u.id = sti.unit_id
                WHERE sti.stock_transfer_id = :transfer_id
            """),
            {"transfer_id": r.id}
        ).fetchall()
        
        transfers.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "transfer_no": r.transfer_no,
            "from_outlet_id": r.from_outlet_id,
            "to_outlet_id": r.to_outlet_id,
            "stock_request_id": r.stock_request_id,
            "status": r.status,
            "shipped_at": r.shipped_at,
            "received_at": r.received_at,
            "created_by": r.created_by,
            "received_by": r.received_by,
            "notes": r.notes,
            "created_at": r.created_at,
            "from_outlet_name": r.from_outlet_name,
            "to_outlet_name": r.to_outlet_name,
            "created_by_name": r.created_by_name,
            "items": [
                {
                    "id": item.id,
                    "stock_transfer_id": item.stock_transfer_id,
                    "ingredient_id": item.ingredient_id,
                    "qty": item.qty,
                    "unit_id": item.unit_id,
                    "unit_cost": item.unit_cost,
                    "total_cost": item.total_cost,
                    "ingredient_name": item.ingredient_name,
                    "unit_symbol": item.unit_symbol
                }
                for item in items
            ]
        })
    
    return transfers


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_stock_transfer(
    data: StockTransferCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Create new stock transfer"""
    
    # Verify outlets
    from_outlet = db.execute(
        text("SELECT id, type FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.from_outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not from_outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="From outlet not found"
        )
    
    to_outlet = db.execute(
        text("SELECT id FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.to_outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not to_outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="To outlet not found"
        )
    
    # Generate transfer number
    transfer_no = generate_transfer_number(str(organization_id), db)
    
    # Insert transfer
    transfer_result = db.execute(
        text("""
            INSERT INTO stock_transfers 
            (organization_id, transfer_no, from_outlet_id, to_outlet_id, 
             stock_request_id, status, created_by, notes)
            VALUES (:org_id, :transfer_no, :from_outlet_id, :to_outlet_id,
                    :stock_request_id, 'DRAFT', :created_by, :notes)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "transfer_no": transfer_no,
            "from_outlet_id": str(data.from_outlet_id),
            "to_outlet_id": str(data.to_outlet_id),
            "stock_request_id": str(data.stock_request_id) if data.stock_request_id else None,
            "created_by": current_user["user_id"],
            "notes": data.notes
        }
    ).fetchone()
    
    transfer_id = transfer_result.id
    
    # Insert items
    for item in data.items:
        # Get unit cost from inventory
        stock = db.execute(
            text("""
                SELECT last_cost
                FROM inventory_stock
                WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
            """),
            {"outlet_id": str(data.from_outlet_id), "ingredient_id": str(item.ingredient_id)}
        ).fetchone()
        
        unit_cost = float(item.unit_cost) if item.unit_cost else (float(stock.last_cost) if stock and stock.last_cost else 0)
        total_cost = float(item.qty) * unit_cost
        
        db.execute(
            text("""
                INSERT INTO stock_transfer_items
                (stock_transfer_id, ingredient_id, qty, unit_id, unit_cost, total_cost)
                VALUES (:transfer_id, :ingredient_id, :qty, :unit_id, :unit_cost, :total_cost)
            """),
            {
                "transfer_id": transfer_id,
                "ingredient_id": str(item.ingredient_id),
                "qty": float(item.qty),
                "unit_id": str(item.unit_id),
                "unit_cost": unit_cost,
                "total_cost": total_cost
            }
        )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock transfer created",
        "transfer_id": str(transfer_id),
        "transfer_no": transfer_no
    }


@router.patch("/{transfer_id}/ship")
def ship_stock_transfer(
    transfer_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Ship stock transfer (deduct from source outlet)"""
    
    transfer = db.execute(
        text("""
            SELECT id, status, from_outlet_id
            FROM stock_transfers
            WHERE id = :transfer_id AND organization_id = :org_id
        """),
        {"transfer_id": str(transfer_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock transfer not found"
        )
    
    if transfer.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot ship transfer with status: {transfer.status}"
        )
    
    # Get items
    items = db.execute(
        text("""
            SELECT ingredient_id, qty, unit_id, unit_cost, total_cost
            FROM stock_transfer_items
            WHERE stock_transfer_id = :transfer_id
        """),
        {"transfer_id": str(transfer_id)}
    ).fetchall()
    
    # Process each item
    for item in items:
        # Check stock availability
        stock = db.execute(
            text("""
                SELECT id, qty_on_hand
                FROM inventory_stock
                WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
            """),
            {"outlet_id": transfer.from_outlet_id, "ingredient_id": item.ingredient_id}
        ).fetchone()
        
        if not stock or float(stock.qty_on_hand) < float(item.qty):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for ingredient {item.ingredient_id}"
            )
        
        # Deduct from source
        new_qty = float(stock.qty_on_hand) - float(item.qty)
        db.execute(
            text("""
                UPDATE inventory_stock
                SET qty_on_hand = :new_qty, updated_at = NOW()
                WHERE id = :stock_id
            """),
            {"new_qty": new_qty, "stock_id": stock.id}
        )
        
        # Create ledger entry (TRANSFER_OUT)
        db.execute(
            text("""
                INSERT INTO inventory_ledger
                (organization_id, outlet_id, ingredient_id, change_qty,
                 source_type, source_id, unit_id, unit_cost, total_cost,
                 remarks)
                VALUES (:org_id, :outlet_id, :ingredient_id, :change_qty,
                        'TRANSFER_OUT', :source_id, :unit_id, :unit_cost, :total_cost,
                        'Stock transferred out')
            """),
            {
                "org_id": str(organization_id),
                "outlet_id": transfer.from_outlet_id,
                "ingredient_id": item.ingredient_id,
                "change_qty": -float(item.qty),
                "source_id": str(transfer_id),
                "unit_id": item.unit_id,
                "unit_cost": float(item.unit_cost) if item.unit_cost else None,
                "total_cost": float(item.total_cost) if item.total_cost else None
            }
        )
    
    # Update transfer status
    db.execute(
        text("""
            UPDATE stock_transfers
            SET status = 'SHIPPED', shipped_at = NOW()
            WHERE id = :transfer_id
        """),
        {"transfer_id": str(transfer_id)}
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock transfer shipped"
    }


@router.patch("/{transfer_id}/receive")
def receive_stock_transfer(
    transfer_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Receive stock transfer (add to destination outlet)"""
    
    transfer = db.execute(
        text("""
            SELECT id, status, to_outlet_id, stock_request_id
            FROM stock_transfers
            WHERE id = :transfer_id AND organization_id = :org_id
        """),
        {"transfer_id": str(transfer_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock transfer not found"
        )
    
    if transfer.status != "SHIPPED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive transfer with status: {transfer.status}"
        )
    
    # Get items
    items = db.execute(
        text("""
            SELECT ingredient_id, qty, unit_id, unit_cost, total_cost
            FROM stock_transfer_items
            WHERE stock_transfer_id = :transfer_id
        """),
        {"transfer_id": str(transfer_id)}
    ).fetchall()
    
    # Process each item
    for item in items:
        # Check if stock exists at destination
        existing_stock = db.execute(
            text("""
                SELECT id, qty_on_hand
                FROM inventory_stock
                WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
            """),
            {"outlet_id": transfer.to_outlet_id, "ingredient_id": item.ingredient_id}
        ).fetchone()
        
        if existing_stock:
            # Update existing
            new_qty = float(existing_stock.qty_on_hand) + float(item.qty)
            db.execute(
                text("""
                    UPDATE inventory_stock
                    SET qty_on_hand = :new_qty,
                        last_cost = :unit_cost,
                        updated_at = NOW()
                    WHERE id = :stock_id
                """),
                {
                    "new_qty": new_qty,
                    "unit_cost": float(item.unit_cost) if item.unit_cost else None,
                    "stock_id": existing_stock.id
                }
            )
        else:
            # Create new
            db.execute(
                text("""
                    INSERT INTO inventory_stock
                    (organization_id, outlet_id, ingredient_id, qty_on_hand,
                     min_qty, unit_id, last_cost)
                    VALUES (:org_id, :outlet_id, :ingredient_id, :qty,
                            0, :unit_id, :unit_cost)
                """),
                {
                    "org_id": str(organization_id),
                    "outlet_id": transfer.to_outlet_id,
                    "ingredient_id": item.ingredient_id,
                    "qty": float(item.qty),
                    "unit_id": item.unit_id,
                    "unit_cost": float(item.unit_cost) if item.unit_cost else None
                }
            )
        
        # Create ledger entry (TRANSFER_IN)
        db.execute(
            text("""
                INSERT INTO inventory_ledger
                (organization_id, outlet_id, ingredient_id, change_qty,
                 source_type, source_id, unit_id, unit_cost, total_cost,
                 remarks)
                VALUES (:org_id, :outlet_id, :ingredient_id, :change_qty,
                        'TRANSFER_IN', :source_id, :unit_id, :unit_cost, :total_cost,
                        'Stock transferred in')
            """),
            {
                "org_id": str(organization_id),
                "outlet_id": transfer.to_outlet_id,
                "ingredient_id": item.ingredient_id,
                "change_qty": float(item.qty),
                "source_id": str(transfer_id),
                "unit_id": item.unit_id,
                "unit_cost": float(item.unit_cost) if item.unit_cost else None,
                "total_cost": float(item.total_cost) if item.total_cost else None
            }
        )
    
    # Update transfer status
    db.execute(
        text("""
            UPDATE stock_transfers
            SET status = 'RECEIVED',
                received_at = NOW(),
                received_by = :received_by
            WHERE id = :transfer_id
        """),
        {"transfer_id": str(transfer_id), "received_by": current_user["user_id"]}
    )
    
    # If linked to stock request, mark as fulfilled
    if transfer.stock_request_id:
        db.execute(
            text("""
                UPDATE stock_requests
                SET status = 'FULFILLED', updated_at = NOW()
                WHERE id = :request_id
            """),
            {"request_id": transfer.stock_request_id}
        )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock transfer received"
    }


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_stock_transfer(
    transfer_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Cancel stock transfer"""
    
    transfer = db.execute(
        text("""
            SELECT id, status
            FROM stock_transfers
            WHERE id = :transfer_id AND organization_id = :org_id
        """),
        {"transfer_id": str(transfer_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock transfer not found"
        )
    
    if transfer.status == "RECEIVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel received transfer"
        )
    
    if transfer.status == "SHIPPED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel shipped transfer. Please receive it first."
        )
    
    db.execute(
        text("""
            UPDATE stock_transfers
            SET status = 'CANCELLED'
            WHERE id = :transfer_id
        """),
        {"transfer_id": str(transfer_id)}
    )
    
    db.commit()
    
    return None