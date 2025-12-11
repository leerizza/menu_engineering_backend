from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationUpdate
)

router = APIRouter()


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's organization details
    """
    org_id = current_user["organization_id"]
    
    result = db.execute(
        text("""
            SELECT id, name, slug, subscription_tier, subscription_status,
                   trial_ends_at, billing_email, max_outlets, max_menu_items,
                   phone, address, created_at, updated_at
            FROM organizations
            WHERE id = :org_id
        """),
        {"org_id": org_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "id": result.id,
        "name": result.name,
        "slug": result.slug,
        "subscription_tier": result.subscription_tier,
        "subscription_status": result.subscription_status,
        "trial_ends_at": result.trial_ends_at,
        "billing_email": result.billing_email,
        "max_outlets": result.max_outlets,
        "max_menu_items": result.max_menu_items,
        "phone": result.phone,
        "address": result.address,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.patch("/me", response_model=OrganizationResponse)
def update_my_organization(
    data: OrganizationUpdate,
    current_user: dict = Depends(require_role("OWNER", "ADMIN")),
    db: Session = Depends(get_db)
):
    """
    Update current user's organization
    Only OWNER or ADMIN can update
    """
    org_id = current_user["organization_id"]
    
    # Build dynamic update query
    update_fields = []
    params = {"org_id": org_id}
    
    if data.name is not None:
        update_fields.append("name = :name")
        params["name"] = data.name
    
    if data.phone is not None:
        update_fields.append("phone = :phone")
        params["phone"] = data.phone
    
    if data.address is not None:
        update_fields.append("address = :address")
        params["address"] = data.address
    
    if data.billing_email is not None:
        update_fields.append("billing_email = :billing_email")
        params["billing_email"] = data.billing_email
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add updated_at
    update_fields.append("updated_at = NOW()")
    
    query = f"""
        UPDATE organizations
        SET {', '.join(update_fields)}
        WHERE id = :org_id
        RETURNING id, name, slug, subscription_tier, subscription_status,
                  trial_ends_at, billing_email, max_outlets, max_menu_items,
                  phone, address, created_at, updated_at
    """
    
    result = db.execute(text(query), params).fetchone()
    db.commit()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "id": result.id,
        "name": result.name,
        "slug": result.slug,
        "subscription_tier": result.subscription_tier,
        "subscription_status": result.subscription_status,
        "trial_ends_at": result.trial_ends_at,
        "billing_email": result.billing_email,
        "max_outlets": result.max_outlets,
        "max_menu_items": result.max_menu_items,
        "phone": result.phone,
        "address": result.address,
        "created_at": result.created_at,
        "updated_at": result.updated_at
    }


@router.get("/stats")
def get_organization_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get organization usage statistics
    """
    org_id = current_user["organization_id"]
    
    # Count outlets
    outlets_count = db.execute(
        text("SELECT COUNT(*) as count FROM outlets WHERE organization_id = :org_id AND is_active = true"),
        {"org_id": org_id}
    ).fetchone().count
    
    # Count menus
    menus_count = db.execute(
        text("SELECT COUNT(*) as count FROM menus WHERE organization_id = :org_id AND is_active = true"),
        {"org_id": org_id}
    ).fetchone().count
    
    # Count users
    users_count = db.execute(
        text("SELECT COUNT(*) as count FROM users WHERE organization_id = :org_id AND is_active = true"),
        {"org_id": org_id}
    ).fetchone().count
    
    # Count ingredients
    ingredients_count = db.execute(
        text("SELECT COUNT(*) as count FROM ingredients WHERE organization_id = :org_id AND is_active = true"),
        {"org_id": org_id}
    ).fetchone().count
    
    # Get organization limits
    org = db.execute(
        text("SELECT max_outlets, max_menu_items FROM organizations WHERE id = :org_id"),
        {"org_id": org_id}
    ).fetchone()
    
    return {
        "usage": {
            "outlets": {
                "current": outlets_count,
                "limit": org.max_outlets
            },
            "menus": {
                "current": menus_count,
                "limit": org.max_menu_items
            },
            "users": users_count,
            "ingredients": ingredients_count
        }
    }