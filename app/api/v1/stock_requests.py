from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.stock_request import (
    StockRequestCreate,
    StockRequestUpdate,
    StockRequestResponse,
    StockRequestItemResponse,
    ApproveStockRequest
)

router = APIRouter()


def generate_request_number(organization_id: str, db: Session) -> str:
    """Generate unique stock request number"""
    today = date.today()
    prefix = f"SR-{today.strftime('%Y%m%d')}"
    
    count = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM stock_requests
            WHERE organization_id = :org_id
            AND DATE(created_at) = :today
        """),
        {"org_id": organization_id, "today": today}
    ).fetchone().count
    
    return f"{prefix}-{count + 1:04d}"


@router.get("/", response_model=List[StockRequestResponse])
def get_all_stock_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    from_outlet_id: Optional[UUID] = Query(None, description="Filter by requesting outlet"),
    to_outlet_id: Optional[UUID] = Query(None, description="Filter by target outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all stock requests"""
    
    query = """
        SELECT 
            sr.id, sr.organization_id, sr.request_no, sr.from_outlet_id, sr.to_outlet_id,
            sr.status, sr.requested_by, sr.approved_by, sr.notes,
            sr.created_at, sr.updated_at, sr.approved_at,
            o1.name as from_outlet_name,
            o2.name as to_outlet_name,
            u1.name as requested_by_name,
            u2.name as approved_by_name
        FROM stock_requests sr
        JOIN outlets o1 ON o1.id = sr.from_outlet_id
        JOIN outlets o2 ON o2.id = sr.to_outlet_id
        JOIN users u1 ON u1.id = sr.requested_by
        LEFT JOIN users u2 ON u2.id = sr.approved_by
        WHERE sr.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if status:
        query += " AND sr.status = :status"
        params["status"] = status
    
    if from_outlet_id:
        query += " AND sr.from_outlet_id = :from_outlet_id"
        params["from_outlet_id"] = str(from_outlet_id)
    
    if to_outlet_id:
        query += " AND sr.to_outlet_id = :to_outlet_id"
        params["to_outlet_id"] = str(to_outlet_id)
    
    query += " ORDER BY sr.created_at DESC"
    
    results = db.execute(text(query), params).fetchall()
    
    # Get items for each request
    requests = []
    for r in results:
        items = db.execute(
            text("""
                SELECT 
                    sri.id, sri.stock_request_id, sri.ingredient_id,
                    sri.requested_qty, sri.requested_unit_id, sri.approved_qty, sri.notes,
                    i.name as ingredient_name,
                    u.symbol as unit_symbol
                FROM stock_request_items sri
                JOIN ingredients i ON i.id = sri.ingredient_id
                JOIN units u ON u.id = sri.requested_unit_id
                WHERE sri.stock_request_id = :request_id
            """),
            {"request_id": r.id}
        ).fetchall()
        
        requests.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "request_no": r.request_no,
            "from_outlet_id": r.from_outlet_id,
            "to_outlet_id": r.to_outlet_id,
            "status": r.status,
            "requested_by": r.requested_by,
            "approved_by": r.approved_by,
            "notes": r.notes,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "approved_at": r.approved_at,
            "from_outlet_name": r.from_outlet_name,
            "to_outlet_name": r.to_outlet_name,
            "requested_by_name": r.requested_by_name,
            "approved_by_name": r.approved_by_name,
            "items": [
                {
                    "id": item.id,
                    "stock_request_id": item.stock_request_id,
                    "ingredient_id": item.ingredient_id,
                    "requested_qty": item.requested_qty,
                    "requested_unit_id": item.requested_unit_id,
                    "approved_qty": item.approved_qty,
                    "notes": item.notes,
                    "ingredient_name": item.ingredient_name,
                    "unit_symbol": item.unit_symbol
                }
                for item in items
            ]
        })
    
    return requests


@router.get("/{request_id}", response_model=StockRequestResponse)
def get_stock_request_by_id(
    request_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get stock request by ID"""
    
    result = db.execute(
        text("""
            SELECT 
                sr.id, sr.organization_id, sr.request_no, sr.from_outlet_id, sr.to_outlet_id,
                sr.status, sr.requested_by, sr.approved_by, sr.notes,
                sr.created_at, sr.updated_at, sr.approved_at,
                o1.name as from_outlet_name,
                o2.name as to_outlet_name,
                u1.name as requested_by_name,
                u2.name as approved_by_name
            FROM stock_requests sr
            JOIN outlets o1 ON o1.id = sr.from_outlet_id
            JOIN outlets o2 ON o2.id = sr.to_outlet_id
            JOIN users u1 ON u1.id = sr.requested_by
            LEFT JOIN users u2 ON u2.id = sr.approved_by
            WHERE sr.id = :request_id AND sr.organization_id = :org_id
        """),
        {"request_id": str(request_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found"
        )
    
    items = db.execute(
        text("""
            SELECT 
                sri.id, sri.stock_request_id, sri.ingredient_id,
                sri.requested_qty, sri.requested_unit_id, sri.approved_qty, sri.notes,
                i.name as ingredient_name,
                u.symbol as unit_symbol
            FROM stock_request_items sri
            JOIN ingredients i ON i.id = sri.ingredient_id
            JOIN units u ON u.id = sri.requested_unit_id
            WHERE sri.stock_request_id = :request_id
        """),
        {"request_id": str(request_id)}
    ).fetchall()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "request_no": result.request_no,
        "from_outlet_id": result.from_outlet_id,
        "to_outlet_id": result.to_outlet_id,
        "status": result.status,
        "requested_by": result.requested_by,
        "approved_by": result.approved_by,
        "notes": result.notes,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "approved_at": result.approved_at,
        "from_outlet_name": result.from_outlet_name,
        "to_outlet_name": result.to_outlet_name,
        "requested_by_name": result.requested_by_name,
        "approved_by_name": result.approved_by_name,
        "items": [
            {
                "id": item.id,
                "stock_request_id": item.stock_request_id,
                "ingredient_id": item.ingredient_id,
                "requested_qty": item.requested_qty,
                "requested_unit_id": item.requested_unit_id,
                "approved_qty": item.approved_qty,
                "notes": item.notes,
                "ingredient_name": item.ingredient_name,
                "unit_symbol": item.unit_symbol
            }
            for item in items
        ]
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_stock_request(
    data: StockRequestCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "OUTLET_MANAGER", "CENTRAL_MANAGER"))
):
    """Create new stock request"""
    
    # Verify from_outlet
    from_outlet = db.execute(
        text("SELECT id, type FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.from_outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not from_outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="From outlet not found"
        )
    
    # Verify to_outlet (should be CENTRAL)
    to_outlet = db.execute(
        text("SELECT id, type FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.to_outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not to_outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="To outlet not found"
        )
    
    if to_outlet.type != "CENTRAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock requests must be sent to CENTRAL outlet"
        )
    
    # Generate request number
    request_no = generate_request_number(str(organization_id), db)
    
    # Insert request
    request_result = db.execute(
        text("""
            INSERT INTO stock_requests 
            (organization_id, request_no, from_outlet_id, to_outlet_id, status, 
             requested_by, notes)
            VALUES (:org_id, :request_no, :from_outlet_id, :to_outlet_id, 'PENDING',
                    :requested_by, :notes)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "request_no": request_no,
            "from_outlet_id": str(data.from_outlet_id),
            "to_outlet_id": str(data.to_outlet_id),
            "requested_by": current_user["user_id"],
            "notes": data.notes
        }
    ).fetchone()
    
    request_id = request_result.id
    
    # Insert items
    for item in data.items:
        db.execute(
            text("""
                INSERT INTO stock_request_items
                (stock_request_id, ingredient_id, requested_qty, requested_unit_id, 
                 approved_qty, notes)
                VALUES (:request_id, :ingredient_id, :requested_qty, :requested_unit_id,
                        0, :notes)
            """),
            {
                "request_id": request_id,
                "ingredient_id": str(item.ingredient_id),
                "requested_qty": float(item.requested_qty),
                "requested_unit_id": str(item.requested_unit_id),
                "notes": item.notes
            }
        )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock request created",
        "request_id": str(request_id),
        "request_no": request_no
    }


@router.patch("/{request_id}/approve")
def approve_stock_request(
    request_id: UUID,
    data: ApproveStockRequest,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Approve stock request and set approved quantities"""
    
    request = db.execute(
        text("""
            SELECT id, status, to_outlet_id
            FROM stock_requests
            WHERE id = :request_id AND organization_id = :org_id
        """),
        {"request_id": str(request_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found"
        )
    
    if request.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request with status: {request.status}"
        )
    
    # Update approved quantities for each item
    for item_data in data.items:
        # Verify item belongs to this request
        item = db.execute(
            text("""
                SELECT id, ingredient_id, requested_qty
                FROM stock_request_items
                WHERE id = :item_id AND stock_request_id = :request_id
            """),
            {"item_id": str(item_data.item_id), "request_id": str(request_id)}
        ).fetchone()
        
        if not item:
            continue
        
        # Check if central has enough stock
        central_stock = db.execute(
            text("""
                SELECT qty_on_hand
                FROM inventory_stock
                WHERE outlet_id = :central_id AND ingredient_id = :ingredient_id
            """),
            {"central_id": request.to_outlet_id, "ingredient_id": item.ingredient_id}
        ).fetchone()
        
        available_qty = float(central_stock.qty_on_hand) if central_stock else 0
        
        # Approved qty cannot exceed requested or available
        max_approved = min(float(item.requested_qty), available_qty)
        approved_qty = min(float(item_data.approved_qty), max_approved)
        
        # Update approved qty
        db.execute(
            text("""
                UPDATE stock_request_items
                SET approved_qty = :approved_qty
                WHERE id = :item_id
            """),
            {"approved_qty": approved_qty, "item_id": str(item_data.item_id)}
        )
    
    # Update request status
    db.execute(
        text("""
            UPDATE stock_requests
            SET status = 'APPROVED',
                approved_by = :approved_by,
                approved_at = NOW(),
                updated_at = NOW()
            WHERE id = :request_id
        """),
        {"approved_by": current_user["user_id"], "request_id": str(request_id)}
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock request approved"
    }


@router.patch("/{request_id}/reject")
def reject_stock_request(
    request_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Reject stock request"""
    
    request = db.execute(
        text("""
            SELECT id, status
            FROM stock_requests
            WHERE id = :request_id AND organization_id = :org_id
        """),
        {"request_id": str(request_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found"
        )
    
    if request.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status: {request.status}"
        )
    
    db.execute(
        text("""
            UPDATE stock_requests
            SET status = 'REJECTED',
                approved_by = :approved_by,
                approved_at = NOW(),
                updated_at = NOW()
            WHERE id = :request_id
        """),
        {"approved_by": current_user["user_id"], "request_id": str(request_id)}
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock request rejected"
    }


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_stock_request(
    request_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "OUTLET_MANAGER", "CENTRAL_MANAGER"))
):
    """Cancel stock request"""
    
    request = db.execute(
        text("""
            SELECT id, status, requested_by
            FROM stock_requests
            WHERE id = :request_id AND organization_id = :org_id
        """),
        {"request_id": str(request_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock request not found"
        )
    
    if request.status not in ["PENDING", "APPROVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status: {request.status}"
        )
    
    db.execute(
        text("""
            UPDATE stock_requests
            SET status = 'CANCELLED', updated_at = NOW()
            WHERE id = :request_id
        """),
        {"request_id": str(request_id)}
    )
    
    db.commit()
    
    return None