from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderItemResponse,
    ReceivePurchaseOrder
)

router = APIRouter()


def generate_po_number(organization_id: str, db: Session) -> str:
    """Generate unique PO number"""
    today = date.today()
    prefix = f"PO-{today.strftime('%Y%m%d')}"
    
    # Get count of POs today
    count = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM purchase_orders
            WHERE organization_id = :org_id
            AND order_date = :today
        """),
        {"org_id": organization_id, "today": today}
    ).fetchone().count
    
    return f"{prefix}-{count + 1:04d}"


@router.get("/", response_model=List[PurchaseOrderResponse])
def get_all_purchase_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all purchase orders"""
    
    query = """
        SELECT 
            po.id, po.organization_id, po.po_no, po.supplier_id, po.outlet_id,
            po.status, po.order_date, po.expected_date, po.received_date,
            po.total_amount, po.notes, po.created_by, po.received_by,
            po.created_at, po.updated_at,
            s.name as supplier_name,
            o.name as outlet_name
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.supplier_id
        JOIN outlets o ON o.id = po.outlet_id
        WHERE po.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if status:
        query += " AND po.status = :status"
        params["status"] = status
    
    if supplier_id:
        query += " AND po.supplier_id = :supplier_id"
        params["supplier_id"] = str(supplier_id)
    
    if outlet_id:
        query += " AND po.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    query += " ORDER BY po.created_at DESC"
    
    results = db.execute(text(query), params).fetchall()
    
    # Get items for each PO
    pos = []
    for r in results:
        items = db.execute(
            text("""
                SELECT 
                    poi.id, poi.purchase_order_id, poi.ingredient_id,
                    poi.qty_ordered, poi.qty_received, poi.unit_id,
                    poi.unit_cost, poi.total_cost, poi.notes,
                    i.name as ingredient_name,
                    u.symbol as unit_symbol
                FROM purchase_order_items poi
                JOIN ingredients i ON i.id = poi.ingredient_id
                JOIN units u ON u.id = poi.unit_id
                WHERE poi.purchase_order_id = :po_id
            """),
            {"po_id": r.id}
        ).fetchall()
        
        pos.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "po_no": r.po_no,
            "supplier_id": r.supplier_id,
            "outlet_id": r.outlet_id,
            "status": r.status,
            "order_date": r.order_date,
            "expected_date": r.expected_date,
            "received_date": r.received_date,
            "total_amount": r.total_amount,
            "notes": r.notes,
            "created_by": r.created_by,
            "received_by": r.received_by,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "supplier_name": r.supplier_name,
            "outlet_name": r.outlet_name,
            "items": [
                {
                    "id": item.id,
                    "purchase_order_id": item.purchase_order_id,
                    "ingredient_id": item.ingredient_id,
                    "qty_ordered": item.qty_ordered,
                    "qty_received": item.qty_received,
                    "unit_id": item.unit_id,
                    "unit_cost": item.unit_cost,
                    "total_cost": item.total_cost,
                    "notes": item.notes,
                    "ingredient_name": item.ingredient_name,
                    "unit_symbol": item.unit_symbol
                }
                for item in items
            ]
        })
    
    return pos


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order_by_id(
    po_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get purchase order by ID"""
    
    result = db.execute(
        text("""
            SELECT 
                po.id, po.organization_id, po.po_no, po.supplier_id, po.outlet_id,
                po.status, po.order_date, po.expected_date, po.received_date,
                po.total_amount, po.notes, po.created_by, po.received_by,
                po.created_at, po.updated_at,
                s.name as supplier_name,
                o.name as outlet_name
            FROM purchase_orders po
            JOIN suppliers s ON s.id = po.supplier_id
            JOIN outlets o ON o.id = po.outlet_id
            WHERE po.id = :po_id AND po.organization_id = :org_id
        """),
        {"po_id": str(po_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    # Get items
    items = db.execute(
        text("""
            SELECT 
                poi.id, poi.purchase_order_id, poi.ingredient_id,
                poi.qty_ordered, poi.qty_received, poi.unit_id,
                poi.unit_cost, poi.total_cost, poi.notes,
                i.name as ingredient_name,
                u.symbol as unit_symbol
            FROM purchase_order_items poi
            JOIN ingredients i ON i.id = poi.ingredient_id
            JOIN units u ON u.id = poi.unit_id
            WHERE poi.purchase_order_id = :po_id
        """),
        {"po_id": str(po_id)}
    ).fetchall()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "po_no": result.po_no,
        "supplier_id": result.supplier_id,
        "outlet_id": result.outlet_id,
        "status": result.status,
        "order_date": result.order_date,
        "expected_date": result.expected_date,
        "received_date": result.received_date,
        "total_amount": result.total_amount,
        "notes": result.notes,
        "created_by": result.created_by,
        "received_by": result.received_by,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "supplier_name": result.supplier_name,
        "outlet_name": result.outlet_name,
        "items": [
            {
                "id": item.id,
                "purchase_order_id": item.purchase_order_id,
                "ingredient_id": item.ingredient_id,
                "qty_ordered": item.qty_ordered,
                "qty_received": item.qty_received,
                "unit_id": item.unit_id,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
                "notes": item.notes,
                "ingredient_name": item.ingredient_name,
                "unit_symbol": item.unit_symbol
            }
            for item in items
        ]
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    data: PurchaseOrderCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Create new purchase order"""
    
    # Verify supplier
    supplier = db.execute(
        text("SELECT id FROM suppliers WHERE id = :supplier_id AND organization_id = :org_id"),
        {"supplier_id": str(data.supplier_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    # Verify outlet
    outlet = db.execute(
        text("SELECT id FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Generate PO number
    po_no = generate_po_number(str(organization_id), db)
    
    # Calculate total amount
    total_amount = sum(item.qty_ordered * item.unit_cost for item in data.items)
    
    # Insert PO
    po_result = db.execute(
        text("""
            INSERT INTO purchase_orders 
            (organization_id, po_no, supplier_id, outlet_id, status, order_date, 
             expected_date, total_amount, notes, created_by)
            VALUES (:org_id, :po_no, :supplier_id, :outlet_id, 'DRAFT', :order_date,
                    :expected_date, :total_amount, :notes, :created_by)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "po_no": po_no,
            "supplier_id": str(data.supplier_id),
            "outlet_id": str(data.outlet_id),
            "order_date": data.order_date,
            "expected_date": data.expected_date,
            "total_amount": float(total_amount),
            "notes": data.notes,
            "created_by": current_user["user_id"]
        }
    ).fetchone()
    
    po_id = po_result.id
    
    # Insert items
    for item in data.items:
        total_cost = item.qty_ordered * item.unit_cost
        
        db.execute(
            text("""
                INSERT INTO purchase_order_items
                (purchase_order_id, ingredient_id, qty_ordered, qty_received,
                 unit_id, unit_cost, total_cost, notes)
                VALUES (:po_id, :ingredient_id, :qty_ordered, 0,
                        :unit_id, :unit_cost, :total_cost, :notes)
            """),
            {
                "po_id": po_id,
                "ingredient_id": str(item.ingredient_id),
                "qty_ordered": float(item.qty_ordered),
                "unit_id": str(item.unit_id),
                "unit_cost": float(item.unit_cost),
                "total_cost": float(total_cost),
                "notes": item.notes
            }
        )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase order created",
        "po_id": str(po_id),
        "po_no": po_no
    }


@router.patch("/{po_id}/approve")
def approve_purchase_order(
    po_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Approve purchase order (change status from DRAFT to ORDERED)"""
    
    po = db.execute(
        text("""
            SELECT id, status
            FROM purchase_orders
            WHERE id = :po_id AND organization_id = :org_id
        """),
        {"po_id": str(po_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    if po.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve PO with status: {po.status}"
        )
    
    db.execute(
        text("""
            UPDATE purchase_orders
            SET status = 'ORDERED', updated_at = NOW()
            WHERE id = :po_id
        """),
        {"po_id": str(po_id)}
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase order approved"
    }


@router.post("/{po_id}/receive")
def receive_purchase_order(
    po_id: UUID,
    data: ReceivePurchaseOrder,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Receive goods from purchase order"""
    
    # Get PO
    po = db.execute(
        text("""
            SELECT id, status, outlet_id
            FROM purchase_orders
            WHERE id = :po_id AND organization_id = :org_id
        """),
        {"po_id": str(po_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    if po.status not in ["ORDERED", "DRAFT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive PO with status: {po.status}"
        )
    
    # Process each item
    for item_data in data.items:
        # Get item details
        item = db.execute(
            text("""
                SELECT ingredient_id, unit_id, unit_cost
                FROM purchase_order_items
                WHERE id = :item_id AND purchase_order_id = :po_id
            """),
            {"item_id": str(item_data.item_id), "po_id": str(po_id)}
        ).fetchone()
        
        if not item:
            continue
        
        # Update item qty_received
        db.execute(
            text("""
                UPDATE purchase_order_items
                SET qty_received = :qty_received
                WHERE id = :item_id
            """),
            {"qty_received": float(item_data.qty_received), "item_id": str(item_data.item_id)}
        )
        
        # Update or create inventory stock
        existing_stock = db.execute(
            text("""
                SELECT id, qty_on_hand
                FROM inventory_stock
                WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
            """),
            {"outlet_id": po.outlet_id, "ingredient_id": item.ingredient_id}
        ).fetchone()
        
        if existing_stock:
            new_qty = float(existing_stock.qty_on_hand) + float(item_data.qty_received)
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
                    "unit_cost": float(item.unit_cost),
                    "stock_id": existing_stock.id
                }
            )
        else:
            db.execute(
                text("""
                    INSERT INTO inventory_stock
                    (organization_id, outlet_id, ingredient_id, qty_on_hand, 
                     min_qty, unit_id, last_cost)
                    VALUES (:org_id, :outlet_id, :ingredient_id, :qty, 0, 
                            :unit_id, :unit_cost)
                """),
                {
                    "org_id": str(organization_id),
                    "outlet_id": po.outlet_id,
                    "ingredient_id": item.ingredient_id,
                    "qty": float(item_data.qty_received),
                    "unit_id": item.unit_id,
                    "unit_cost": float(item.unit_cost)
                }
            )
        
        # Create ledger entry
        total_cost = float(item_data.qty_received) * float(item.unit_cost)
        db.execute(
            text("""
                INSERT INTO inventory_ledger
                (organization_id, outlet_id, ingredient_id, change_qty,
                 source_type, source_id, unit_id, unit_cost, total_cost,
                 remarks)
                VALUES (:org_id, :outlet_id, :ingredient_id, :change_qty,
                        'PURCHASE', :source_id, :unit_id, :unit_cost, :total_cost,
                        :remarks)
            """),
            {
                "org_id": str(organization_id),
                "outlet_id": po.outlet_id,
                "ingredient_id": item.ingredient_id,
                "change_qty": float(item_data.qty_received),
                "source_id": str(po_id),
                "unit_id": item.unit_id,
                "unit_cost": float(item.unit_cost),
                "total_cost": total_cost,
                "remarks": f"Received from PO"
            }
        )
    
    # Update PO status
    db.execute(
        text("""
            UPDATE purchase_orders
            SET status = 'RECEIVED',
                received_date = :received_date,
                received_by = :received_by,
                updated_at = NOW()
            WHERE id = :po_id
        """),
        {
            "received_date": data.received_date,
            "received_by": current_user["user_id"],
            "po_id": str(po_id)
        }
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Purchase order received successfully"
    }


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_purchase_order(
    po_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Cancel purchase order"""
    
    po = db.execute(
        text("""
            SELECT id, status
            FROM purchase_orders
            WHERE id = :po_id AND organization_id = :org_id
        """),
        {"po_id": str(po_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found"
        )
    
    if po.status == "RECEIVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel received purchase order"
        )
    
    db.execute(
        text("""
            UPDATE purchase_orders
            SET status = 'CANCELLED', updated_at = NOW()
            WHERE id = :po_id
        """),
        {"po_id": str(po_id)}
    )
    
    db.commit()
    
    return None