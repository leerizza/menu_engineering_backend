from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.inventory import (
    InventoryStockResponse,
    InventoryLedgerResponse,
    InventoryAdjustmentCreate
)

router = APIRouter()


@router.get("/stock", response_model=List[InventoryStockResponse])
def get_inventory_stock(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get inventory stock levels"""
    
    query = """
        SELECT 
            s.id, s.outlet_id, s.ingredient_id, s.qty_on_hand, s.min_qty,
            s.unit_id, s.last_cost, s.updated_at,
            o.name as outlet_name,
            i.name as ingredient_name,
            u.symbol as unit_symbol,
            CASE WHEN s.qty_on_hand <= s.min_qty THEN true ELSE false END as is_low_stock
        FROM inventory_stock s
        JOIN outlets o ON o.id = s.outlet_id
        JOIN ingredients i ON i.id = s.ingredient_id
        JOIN units u ON u.id = s.unit_id
        WHERE s.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if outlet_id:
        query += " AND s.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    if low_stock_only:
        query += " AND s.qty_on_hand <= s.min_qty"
    
    query += " ORDER BY o.name, i.name"
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {
            "id": r.id,
            "outlet_id": r.outlet_id,
            "ingredient_id": r.ingredient_id,
            "qty_on_hand": r.qty_on_hand,
            "min_qty": r.min_qty,
            "unit_id": r.unit_id,
            "last_cost": r.last_cost,
            "updated_at": r.updated_at,
            "outlet_name": r.outlet_name,
            "ingredient_name": r.ingredient_name,
            "unit_symbol": r.unit_symbol,
            "is_low_stock": r.is_low_stock
        }
        for r in results
    ]


@router.get("/stock/{outlet_id}/{ingredient_id}")
def get_stock_by_outlet_ingredient(
    outlet_id: UUID,
    ingredient_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get specific stock item"""
    
    result = db.execute(
        text("""
            SELECT 
                s.id, s.outlet_id, s.ingredient_id, s.qty_on_hand, s.min_qty,
                s.unit_id, s.last_cost, s.updated_at,
                o.name as outlet_name,
                i.name as ingredient_name,
                u.symbol as unit_symbol
            FROM inventory_stock s
            JOIN outlets o ON o.id = s.outlet_id
            JOIN ingredients i ON i.id = s.ingredient_id
            JOIN units u ON u.id = s.unit_id
            WHERE s.outlet_id = :outlet_id 
            AND s.ingredient_id = :ingredient_id
            AND s.organization_id = :org_id
        """),
        {
            "outlet_id": str(outlet_id),
            "ingredient_id": str(ingredient_id),
            "org_id": str(organization_id)
        }
    ).fetchone()
    
    if not result:
        return {
            "qty_on_hand": 0,
            "message": "No stock record found"
        }
    
    return {
        "id": result.id,
        "outlet_id": result.outlet_id,
        "ingredient_id": result.ingredient_id,
        "qty_on_hand": float(result.qty_on_hand),
        "min_qty": float(result.min_qty),
        "unit_id": result.unit_id,
        "last_cost": float(result.last_cost) if result.last_cost else None,
        "updated_at": result.updated_at,
        "outlet_name": result.outlet_name,
        "ingredient_name": result.ingredient_name,
        "unit_symbol": result.unit_symbol
    }


@router.get("/ledger", response_model=List[InventoryLedgerResponse])
def get_inventory_ledger(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    ingredient_id: Optional[UUID] = Query(None, description="Filter by ingredient"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    limit: int = Query(100, le=1000, description="Limit results"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get inventory ledger (audit trail)"""
    
    query = """
        SELECT 
            l.id, l.outlet_id, l.ingredient_id, l.change_qty, l.source_type,
            l.source_id, l.unit_id, l.unit_cost, l.total_cost, l.remarks, l.created_at,
            o.name as outlet_name,
            i.name as ingredient_name,
            u.symbol as unit_symbol
        FROM inventory_ledger l
        JOIN outlets o ON o.id = l.outlet_id
        JOIN ingredients i ON i.id = l.ingredient_id
        JOIN units u ON u.id = l.unit_id
        WHERE l.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if outlet_id:
        query += " AND l.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    if ingredient_id:
        query += " AND l.ingredient_id = :ingredient_id"
        params["ingredient_id"] = str(ingredient_id)
    
    if source_type:
        query += " AND l.source_type = :source_type"
        params["source_type"] = source_type
    
    query += " ORDER BY l.created_at DESC LIMIT :limit"
    params["limit"] = limit
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {
            "id": r.id,
            "outlet_id": r.outlet_id,
            "ingredient_id": r.ingredient_id,
            "change_qty": r.change_qty,
            "source_type": r.source_type,
            "source_id": r.source_id,
            "unit_id": r.unit_id,
            "unit_cost": r.unit_cost,
            "total_cost": r.total_cost,
            "remarks": r.remarks,
            "created_at": r.created_at,
            "outlet_name": r.outlet_name,
            "ingredient_name": r.ingredient_name,
            "unit_symbol": r.unit_symbol
        }
        for r in results
    ]


@router.post("/adjustment")
def create_inventory_adjustment(
    data: InventoryAdjustmentCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Create manual inventory adjustment"""
    
    # Verify outlet belongs to org
    outlet = db.execute(
        text("SELECT id FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Verify ingredient belongs to org
    ingredient = db.execute(
        text("SELECT id FROM ingredients WHERE id = :ingredient_id AND organization_id = :org_id"),
        {"ingredient_id": str(data.ingredient_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    # Check if stock record exists
    existing_stock = db.execute(
        text("""
            SELECT id, qty_on_hand 
            FROM inventory_stock 
            WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
        """),
        {"outlet_id": str(data.outlet_id), "ingredient_id": str(data.ingredient_id)}
    ).fetchone()
    
    if existing_stock:
        # Update existing stock
        new_qty = float(existing_stock.qty_on_hand) + float(data.adjustment_qty)
        
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment would result in negative stock"
            )
        
        db.execute(
            text("""
                UPDATE inventory_stock
                SET qty_on_hand = :new_qty, updated_at = NOW()
                WHERE id = :stock_id
            """),
            {"new_qty": new_qty, "stock_id": existing_stock.id}
        )
    else:
        # Create new stock record
        if data.adjustment_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create new stock with negative quantity"
            )
        
        db.execute(
            text("""
                INSERT INTO inventory_stock 
                (organization_id, outlet_id, ingredient_id, qty_on_hand, min_qty, unit_id)
                VALUES (:org_id, :outlet_id, :ingredient_id, :qty, 0, :unit_id)
            """),
            {
                "org_id": str(organization_id),
                "outlet_id": str(data.outlet_id),
                "ingredient_id": str(data.ingredient_id),
                "qty": float(data.adjustment_qty),
                "unit_id": str(data.unit_id)
            }
        )
    
    # Create ledger entry
    ledger_result = db.execute(
        text("""
            INSERT INTO inventory_ledger
            (organization_id, outlet_id, ingredient_id, change_qty, source_type, 
             unit_id, remarks)
            VALUES (:org_id, :outlet_id, :ingredient_id, :change_qty, 'ADJUSTMENT',
                    :unit_id, :remarks)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "outlet_id": str(data.outlet_id),
            "ingredient_id": str(data.ingredient_id),
            "change_qty": float(data.adjustment_qty),
            "unit_id": str(data.unit_id),
            "remarks": data.remarks
        }
    ).fetchone()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Inventory adjustment created",
        "ledger_id": str(ledger_result.id)
    }


@router.get("/low-stock-alerts")
def get_low_stock_alerts(
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get list of low stock items across all outlets"""
    
    results = db.execute(
        text("""
            SELECT 
                o.name as outlet_name,
                i.name as ingredient_name,
                s.qty_on_hand,
                s.min_qty,
                u.symbol as unit_symbol,
                o.type as outlet_type
            FROM inventory_stock s
            JOIN outlets o ON o.id = s.outlet_id
            JOIN ingredients i ON i.id = s.ingredient_id
            JOIN units u ON u.id = s.unit_id
            WHERE s.organization_id = :org_id
            AND s.qty_on_hand <= s.min_qty
            ORDER BY 
                CASE WHEN o.type = 'CENTRAL' THEN 0 ELSE 1 END,
                s.qty_on_hand ASC
        """),
        {"org_id": str(organization_id)}
    ).fetchall()
    
    return {
        "total_alerts": len(results),
        "items": [
            {
                "outlet_name": r.outlet_name,
                "outlet_type": r.outlet_type,
                "ingredient_name": r.ingredient_name,
                "qty_on_hand": float(r.qty_on_hand),
                "min_qty": float(r.min_qty),
                "unit_symbol": r.unit_symbol,
                "shortage": float(r.min_qty - r.qty_on_hand)
            }
            for r in results
        ]
    }