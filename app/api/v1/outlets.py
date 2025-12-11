from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.outlet import (
    OutletCreate,
    OutletUpdate,
    OutletResponse
)

router = APIRouter()


@router.get("/", response_model=List[OutletResponse])
def get_all_outlets(
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all outlets in the organization
    """
    results = db.execute(
        text("""
            SELECT id, organization_id, name, code, type, address, phone, 
                   is_active, created_at, updated_at
            FROM outlets
            WHERE organization_id = :org_id
            ORDER BY 
                CASE 
                    WHEN type = 'CENTRAL' THEN 0 
                    ELSE 1 
                END,
                created_at ASC
        """),
        {"org_id": str(organization_id)}
    ).fetchall()
    
    return [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "name": r.name,
            "code": r.code,
            "type": r.type,
            "address": r.address,
            "phone": r.phone,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        }
        for r in results
    ]


@router.get("/{outlet_id}", response_model=OutletResponse)
def get_outlet_by_id(
    outlet_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get outlet by ID
    """
    result = db.execute(
        text("""
            SELECT id, organization_id, name, code, type, address, phone, 
                   is_active, created_at, updated_at
            FROM outlets
            WHERE id = :outlet_id AND organization_id = :org_id
        """),
        {"outlet_id": str(outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "code": result.code,
        "type": result.type,
        "address": result.address,
        "phone": result.phone,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.post("/", response_model=OutletResponse, status_code=status.HTTP_201_CREATED)
def create_outlet(
    data: OutletCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """
    Create new outlet
    Only OWNER, ADMIN, or CENTRAL_MANAGER can create outlets
    """
    # Check outlet limit
    org = db.execute(
        text("SELECT max_outlets FROM organizations WHERE id = :org_id"),
        {"org_id": str(organization_id)}
    ).fetchone()
    
    current_count = db.execute(
        text("SELECT COUNT(*) as count FROM outlets WHERE organization_id = :org_id"),
        {"org_id": str(organization_id)}
    ).fetchone().count
    
    if current_count >= org.max_outlets:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Outlet limit reached. Maximum {org.max_outlets} outlets allowed for your plan."
        )
    
    # Check if code already exists
    existing = db.execute(
        text("SELECT id FROM outlets WHERE organization_id = :org_id AND code = :code"),
        {"org_id": str(organization_id), "code": data.code}
    ).fetchone()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Outlet code '{data.code}' already exists"
        )
    
    # Validate type
    if data.type not in ["CENTRAL", "OUTLET"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type must be either 'CENTRAL' or 'OUTLET'"
        )
    
    # Insert outlet
    result = db.execute(
        text("""
            INSERT INTO outlets (organization_id, name, code, type, address, phone, is_active)
            VALUES (:org_id, :name, :code, :type, :address, :phone, true)
            RETURNING id, organization_id, name, code, type, address, phone, 
                      is_active, created_at, updated_at
        """),
        {
            "org_id": str(organization_id),
            "name": data.name,
            "code": data.code,
            "type": data.type,
            "address": data.address,
            "phone": data.phone
        }
    ).fetchone()
    
    db.commit()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "code": result.code,
        "type": result.type,
        "address": result.address,
        "phone": result.phone,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.patch("/{outlet_id}", response_model=OutletResponse)
def update_outlet(
    outlet_id: UUID,
    data: OutletUpdate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """
    Update outlet
    Only OWNER, ADMIN, or CENTRAL_MANAGER can update outlets
    """
    # Check if outlet exists
    existing = db.execute(
        text("SELECT id FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Build dynamic update query
    update_fields = []
    params = {"outlet_id": str(outlet_id), "org_id": str(organization_id)}
    
    if data.name is not None:
        update_fields.append("name = :name")
        params["name"] = data.name
    
    if data.address is not None:
        update_fields.append("address = :address")
        params["address"] = data.address
    
    if data.phone is not None:
        update_fields.append("phone = :phone")
        params["phone"] = data.phone
    
    if data.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = data.is_active
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add updated_at
    update_fields.append("updated_at = NOW()")
    
    query = f"""
        UPDATE outlets
        SET {', '.join(update_fields)}
        WHERE id = :outlet_id AND organization_id = :org_id
        RETURNING id, organization_id, name, code, type, address, phone, 
                  is_active, created_at, updated_at
    """
    
    result = db.execute(text(query), params).fetchone()
    db.commit()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "code": result.code,
        "type": result.type,
        "address": result.address,
        "phone": result.phone,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.delete("/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outlet(
    outlet_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN"))
):
    """
    Delete outlet (soft delete - set is_active to false)
    Only OWNER or ADMIN can delete outlets
    """
    # Check if outlet exists
    existing = db.execute(
        text("SELECT id, type FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Don't allow deleting CENTRAL outlet if it's the only one
    if existing.type == "CENTRAL":
        central_count = db.execute(
            text("SELECT COUNT(*) as count FROM outlets WHERE organization_id = :org_id AND type = 'CENTRAL' AND is_active = true"),
            {"org_id": str(organization_id)}
        ).fetchone().count
        
        if central_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only central outlet"
            )
    
    # Soft delete
    db.execute(
        text("UPDATE outlets SET is_active = false, updated_at = NOW() WHERE id = :outlet_id"),
        {"outlet_id": str(outlet_id)}
    )
    db.commit()
    
    return None


@router.get("/{outlet_id}/inventory-summary")
def get_outlet_inventory_summary(
    outlet_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get inventory summary for an outlet
    """
    # Check if outlet exists
    outlet = db.execute(
        text("SELECT id, name FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Get inventory stats
    stats = db.execute(
        text("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN qty_on_hand <= min_qty THEN 1 END) as low_stock_items,
                COUNT(CASE WHEN qty_on_hand = 0 THEN 1 END) as out_of_stock_items
            FROM inventory_stock
            WHERE outlet_id = :outlet_id
        """),
        {"outlet_id": str(outlet_id)}
    ).fetchone()
    
    return {
        "outlet_id": str(outlet_id),
        "outlet_name": outlet.name,
        "total_items": stats.total_items,
        "low_stock_items": stats.low_stock_items,
        "out_of_stock_items": stats.out_of_stock_items
    }