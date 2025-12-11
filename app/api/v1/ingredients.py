from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientUpdate,
    IngredientResponse
)

router = APIRouter()


@router.get("/", response_model=List[IngredientResponse])
def get_all_ingredients(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or SKU"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all ingredients with optional filters"""
    
    query = """
        SELECT 
            i.id, i.organization_id, i.name, i.category, i.sku,
            i.base_unit_id, i.is_active, i.created_at, i.updated_at,
            u.name as base_unit_name, u.symbol as base_unit_symbol
        FROM ingredients i
        LEFT JOIN units u ON u.id = i.base_unit_id
        WHERE i.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if category:
        query += " AND i.category = :category"
        params["category"] = category
    
    if search:
        query += " AND (i.name ILIKE :search OR i.sku ILIKE :search)"
        params["search"] = f"%{search}%"
    
    if is_active is not None:
        query += " AND i.is_active = :is_active"
        params["is_active"] = is_active
    
    query += " ORDER BY i.name ASC"
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "name": r.name,
            "category": r.category,
            "sku": r.sku,
            "base_unit_id": r.base_unit_id,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "base_unit_name": r.base_unit_name,
            "base_unit_symbol": r.base_unit_symbol
        }
        for r in results
    ]


@router.get("/categories")
def get_ingredient_categories(
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get list of unique ingredient categories"""
    
    results = db.execute(
        text("""
            SELECT DISTINCT category
            FROM ingredients
            WHERE organization_id = :org_id AND category IS NOT NULL
            ORDER BY category
        """),
        {"org_id": str(organization_id)}
    ).fetchall()
    
    return {"categories": [r.category for r in results]}


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient_by_id(
    ingredient_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get ingredient by ID"""
    
    result = db.execute(
        text("""
            SELECT 
                i.id, i.organization_id, i.name, i.category, i.sku,
                i.base_unit_id, i.is_active, i.created_at, i.updated_at,
                u.name as base_unit_name, u.symbol as base_unit_symbol
            FROM ingredients i
            LEFT JOIN units u ON u.id = i.base_unit_id
            WHERE i.id = :ingredient_id AND i.organization_id = :org_id
        """),
        {"ingredient_id": str(ingredient_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "category": result.category,
        "sku": result.sku,
        "base_unit_id": result.base_unit_id,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "base_unit_name": result.base_unit_name,
        "base_unit_symbol": result.base_unit_symbol
    }


@router.post("/", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    data: IngredientCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Create new ingredient"""
    
    # Check if SKU already exists
    if data.sku:
        existing = db.execute(
            text("SELECT id FROM ingredients WHERE organization_id = :org_id AND sku = :sku"),
            {"org_id": str(organization_id), "sku": data.sku}
        ).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{data.sku}' already exists"
            )
    
    # Verify unit exists
    unit = db.execute(
        text("SELECT id FROM units WHERE id = :unit_id"),
        {"unit_id": str(data.base_unit_id)}
    ).fetchone()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base_unit_id"
        )
    
    # Insert ingredient
    result = db.execute(
        text("""
            INSERT INTO ingredients (organization_id, name, category, sku, base_unit_id, is_active)
            VALUES (:org_id, :name, :category, :sku, :base_unit_id, true)
            RETURNING id, organization_id, name, category, sku, base_unit_id, 
                      is_active, created_at, updated_at
        """),
        {
            "org_id": str(organization_id),
            "name": data.name,
            "category": data.category,
            "sku": data.sku,
            "base_unit_id": str(data.base_unit_id)
        }
    ).fetchone()
    
    db.commit()
    
    # Get unit info
    unit_info = db.execute(
        text("SELECT name, symbol FROM units WHERE id = :unit_id"),
        {"unit_id": str(data.base_unit_id)}
    ).fetchone()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "category": result.category,
        "sku": result.sku,
        "base_unit_id": result.base_unit_id,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "base_unit_name": unit_info.name,
        "base_unit_symbol": unit_info.symbol
    }


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: UUID,
    data: IngredientUpdate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Update ingredient"""
    
    # Check if exists
    existing = db.execute(
        text("SELECT id FROM ingredients WHERE id = :ingredient_id AND organization_id = :org_id"),
        {"ingredient_id": str(ingredient_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    # Check SKU uniqueness if updating
    if data.sku:
        sku_check = db.execute(
            text("""
                SELECT id FROM ingredients 
                WHERE organization_id = :org_id AND sku = :sku AND id != :ingredient_id
            """),
            {"org_id": str(organization_id), "sku": data.sku, "ingredient_id": str(ingredient_id)}
        ).fetchone()
        
        if sku_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{data.sku}' already exists"
            )
    
    # Build update query
    update_fields = []
    params = {"ingredient_id": str(ingredient_id), "org_id": str(organization_id)}
    
    if data.name is not None:
        update_fields.append("name = :name")
        params["name"] = data.name
    
    if data.category is not None:
        update_fields.append("category = :category")
        params["category"] = data.category
    
    if data.sku is not None:
        update_fields.append("sku = :sku")
        params["sku"] = data.sku
    
    if data.base_unit_id is not None:
        # Verify unit exists
        unit = db.execute(
            text("SELECT id FROM units WHERE id = :unit_id"),
            {"unit_id": str(data.base_unit_id)}
        ).fetchone()
        
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base_unit_id"
            )
        
        update_fields.append("base_unit_id = :base_unit_id")
        params["base_unit_id"] = str(data.base_unit_id)
    
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
        UPDATE ingredients
        SET {', '.join(update_fields)}
        WHERE id = :ingredient_id AND organization_id = :org_id
        RETURNING id, organization_id, name, category, sku, base_unit_id,
                  is_active, created_at, updated_at
    """
    
    result = db.execute(text(query), params).fetchone()
    db.commit()
    
    # Get unit info
    unit_info = db.execute(
        text("SELECT name, symbol FROM units WHERE id = :unit_id"),
        {"unit_id": str(result.base_unit_id)}
    ).fetchone()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "category": result.category,
        "sku": result.sku,
        "base_unit_id": result.base_unit_id,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "base_unit_name": unit_info.name,
        "base_unit_symbol": unit_info.symbol
    }


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN"))
):
    """Delete ingredient (soft delete)"""
    
    existing = db.execute(
        text("SELECT id FROM ingredients WHERE id = :ingredient_id AND organization_id = :org_id"),
        {"ingredient_id": str(ingredient_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    # Check if used in recipes
    used_in_recipes = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM recipe_items ri
            JOIN recipes r ON r.id = ri.recipe_id
            JOIN menus m ON m.id = r.menu_id
            WHERE ri.ingredient_id = :ingredient_id
            AND m.organization_id = :org_id
        """),
        {"ingredient_id": str(ingredient_id), "org_id": str(organization_id)}
    ).fetchone().count
    
    if used_in_recipes > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete ingredient. It is used in {used_in_recipes} recipe(s)"
        )
    
    # Soft delete
    db.execute(
        text("UPDATE ingredients SET is_active = false, updated_at = NOW() WHERE id = :ingredient_id"),
        {"ingredient_id": str(ingredient_id)}
    )
    db.commit()
    
    return None