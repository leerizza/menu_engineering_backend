from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse
)

router = APIRouter()


@router.get("/", response_model=List[SupplierResponse])
def get_all_suppliers(
    search: Optional[str] = Query(None, description="Search by name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all suppliers"""
    
    query = """
        SELECT id, organization_id, name, contact_person, phone, email, address,
               is_active, created_at, updated_at
        FROM suppliers
        WHERE organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if search:
        query += " AND name ILIKE :search"
        params["search"] = f"%{search}%"
    
    if is_active is not None:
        query += " AND is_active = :is_active"
        params["is_active"] = is_active
    
    query += " ORDER BY name ASC"
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "name": r.name,
            "contact_person": r.contact_person,
            "phone": r.phone,
            "email": r.email,
            "address": r.address,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        }
        for r in results
    ]


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier_by_id(
    supplier_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get supplier by ID"""
    
    result = db.execute(
        text("""
            SELECT id, organization_id, name, contact_person, phone, email, address,
                   is_active, created_at, updated_at
            FROM suppliers
            WHERE id = :supplier_id AND organization_id = :org_id
        """),
        {"supplier_id": str(supplier_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "contact_person": result.contact_person,
        "phone": result.phone,
        "email": result.email,
        "address": result.address,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    data: SupplierCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Create new supplier"""
    
    result = db.execute(
        text("""
            INSERT INTO suppliers (organization_id, name, contact_person, phone, email, address, is_active)
            VALUES (:org_id, :name, :contact_person, :phone, :email, :address, true)
            RETURNING id, organization_id, name, contact_person, phone, email, address,
                      is_active, created_at, updated_at
        """),
        {
            "org_id": str(organization_id),
            "name": data.name,
            "contact_person": data.contact_person,
            "phone": data.phone,
            "email": data.email,
            "address": data.address
        }
    ).fetchone()
    
    db.commit()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "contact_person": result.contact_person,
        "phone": result.phone,
        "email": result.email,
        "address": result.address,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "CENTRAL_STAFF"))
):
    """Update supplier"""
    
    existing = db.execute(
        text("SELECT id FROM suppliers WHERE id = :supplier_id AND organization_id = :org_id"),
        {"supplier_id": str(supplier_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    update_fields = []
    params = {"supplier_id": str(supplier_id), "org_id": str(organization_id)}
    
    if data.name is not None:
        update_fields.append("name = :name")
        params["name"] = data.name
    
    if data.contact_person is not None:
        update_fields.append("contact_person = :contact_person")
        params["contact_person"] = data.contact_person
    
    if data.phone is not None:
        update_fields.append("phone = :phone")
        params["phone"] = data.phone
    
    if data.email is not None:
        update_fields.append("email = :email")
        params["email"] = data.email
    
    if data.address is not None:
        update_fields.append("address = :address")
        params["address"] = data.address
    
    if data.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = data.is_active
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_fields.append("updated_at = NOW()")
    
    query = f"""
        UPDATE suppliers
        SET {', '.join(update_fields)}
        WHERE id = :supplier_id AND organization_id = :org_id
        RETURNING id, organization_id, name, contact_person, phone, email, address,
                  is_active, created_at, updated_at
    """
    
    result = db.execute(text(query), params).fetchone()
    db.commit()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "contact_person": result.contact_person,
        "phone": result.phone,
        "email": result.email,
        "address": result.address,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN"))
):
    """Delete supplier (soft delete)"""
    
    existing = db.execute(
        text("SELECT id FROM suppliers WHERE id = :supplier_id AND organization_id = :org_id"),
        {"supplier_id": str(supplier_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    # Check if has active purchase orders
    active_pos = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM purchase_orders
            WHERE supplier_id = :supplier_id 
            AND status IN ('DRAFT', 'ORDERED')
        """),
        {"supplier_id": str(supplier_id)}
    ).fetchone().count
    
    if active_pos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete supplier. It has {active_pos} active purchase order(s)"
        )
    
    db.execute(
        text("UPDATE suppliers SET is_active = false, updated_at = NOW() WHERE id = :supplier_id"),
        {"supplier_id": str(supplier_id)}
    )
    db.commit()
    
    return None