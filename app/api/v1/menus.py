from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.menu import (
    MenuCreate,
    MenuUpdate,
    MenuResponse,
    RecipeCreate,
    RecipeResponse,
    RecipeItemResponse
)

router = APIRouter()


@router.get("/", response_model=List[MenuResponse])
def get_all_menus(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all menus with active recipes"""
    
    query = """
        SELECT 
            m.id, m.organization_id, m.name, m.category, m.price,
            m.description, m.image_url, m.is_active, m.created_at, m.updated_at
        FROM menus m
        WHERE m.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if category:
        query += " AND m.category = :category"
        params["category"] = category
    
    if is_active is not None:
        query += " AND m.is_active = :is_active"
        params["is_active"] = is_active
    
    if search:
        query += " AND m.name ILIKE :search"
        params["search"] = f"%{search}%"
    
    query += " ORDER BY m.category, m.name"
    
    results = db.execute(text(query), params).fetchall()
    
    menus = []
    for r in results:
        # Get active recipe
        recipe = db.execute(
            text("""
                SELECT id, menu_id, version, is_active, notes, created_at, updated_at
                FROM recipes
                WHERE menu_id = :menu_id AND is_active = true
                ORDER BY version DESC
                LIMIT 1
            """),
            {"menu_id": r.id}
        ).fetchone()
        
        active_recipe = None
        hpp = None
        
        if recipe:
            # Get recipe items
            items = db.execute(
                text("""
                    SELECT 
                        ri.id, ri.recipe_id, ri.ingredient_id, ri.qty, ri.unit_id,
                        i.name as ingredient_name,
                        u.symbol as unit_symbol,
                        s.last_cost as ingredient_cost
                    FROM recipe_items ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    JOIN units u ON u.id = ri.unit_id
                    LEFT JOIN inventory_stock s ON s.ingredient_id = ri.ingredient_id
                        AND s.outlet_id = (SELECT id FROM outlets WHERE organization_id = :org_id AND type = 'CENTRAL' LIMIT 1)
                    WHERE ri.recipe_id = :recipe_id
                """),
                {"recipe_id": recipe.id, "org_id": str(organization_id)}
            ).fetchall()
            
            # Calculate HPP (total cost)
            total_cost = Decimal(0)
            recipe_items = []
            
            for item in items:
                item_cost = Decimal(0)
                if item.ingredient_cost:
                    item_cost = Decimal(str(item.qty)) * Decimal(str(item.ingredient_cost))
                    total_cost += item_cost
                
                recipe_items.append({
                    "id": item.id,
                    "recipe_id": item.recipe_id,
                    "ingredient_id": item.ingredient_id,
                    "qty": item.qty,
                    "unit_id": item.unit_id,
                    "ingredient_name": item.ingredient_name,
                    "unit_symbol": item.unit_symbol,
                    "ingredient_cost": item_cost
                })
            
            hpp = total_cost
            
            active_recipe = {
                "id": recipe.id,
                "menu_id": recipe.menu_id,
                "version": recipe.version,
                "is_active": recipe.is_active,
                "notes": recipe.notes,
                "created_at": recipe.created_at,
                "updated_at": recipe.updated_at,
                "items": recipe_items,
                "total_cost": total_cost
            }
        
        # Calculate profit margin
        profit_margin = None
        if hpp and hpp > 0:
            profit_margin = ((Decimal(str(r.price)) - hpp) / Decimal(str(r.price))) * 100
        
        menus.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "name": r.name,
            "category": r.category,
            "price": r.price,
            "description": r.description,
            "image_url": r.image_url,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "active_recipe": active_recipe,
            "hpp": hpp,
            "profit_margin": profit_margin
        })
    
    return menus


@router.get("/categories")
def get_menu_categories(
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get list of unique menu categories"""
    
    results = db.execute(
        text("""
            SELECT DISTINCT category
            FROM menus
            WHERE organization_id = :org_id AND category IS NOT NULL
            ORDER BY category
        """),
        {"org_id": str(organization_id)}
    ).fetchall()
    
    return {"categories": [r.category for r in results]}


@router.get("/{menu_id}", response_model=MenuResponse)
def get_menu_by_id(
    menu_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get menu by ID with active recipe"""
    
    result = db.execute(
        text("""
            SELECT 
                m.id, m.organization_id, m.name, m.category, m.price,
                m.description, m.image_url, m.is_active, m.created_at, m.updated_at
            FROM menus m
            WHERE m.id = :menu_id AND m.organization_id = :org_id
        """),
        {"menu_id": str(menu_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    # Get active recipe (same logic as above)
    recipe = db.execute(
        text("""
            SELECT id, menu_id, version, is_active, notes, created_at, updated_at
            FROM recipes
            WHERE menu_id = :menu_id AND is_active = true
            ORDER BY version DESC
            LIMIT 1
        """),
        {"menu_id": result.id}
    ).fetchone()
    
    active_recipe = None
    hpp = None
    
    if recipe:
        items = db.execute(
            text("""
                SELECT 
                    ri.id, ri.recipe_id, ri.ingredient_id, ri.qty, ri.unit_id,
                    i.name as ingredient_name,
                    u.symbol as unit_symbol,
                    s.last_cost as ingredient_cost
                FROM recipe_items ri
                JOIN ingredients i ON i.id = ri.ingredient_id
                JOIN units u ON u.id = ri.unit_id
                LEFT JOIN inventory_stock s ON s.ingredient_id = ri.ingredient_id
                    AND s.outlet_id = (SELECT id FROM outlets WHERE organization_id = :org_id AND type = 'CENTRAL' LIMIT 1)
                WHERE ri.recipe_id = :recipe_id
            """),
            {"recipe_id": recipe.id, "org_id": str(organization_id)}
        ).fetchall()
        
        total_cost = Decimal(0)
        recipe_items = []
        
        for item in items:
            item_cost = Decimal(0)
            if item.ingredient_cost:
                item_cost = Decimal(str(item.qty)) * Decimal(str(item.ingredient_cost))
                total_cost += item_cost
            
            recipe_items.append({
                "id": item.id,
                "recipe_id": item.recipe_id,
                "ingredient_id": item.ingredient_id,
                "qty": item.qty,
                "unit_id": item.unit_id,
                "ingredient_name": item.ingredient_name,
                "unit_symbol": item.unit_symbol,
                "ingredient_cost": item_cost
            })
        
        hpp = total_cost
        
        active_recipe = {
            "id": recipe.id,
            "menu_id": recipe.menu_id,
            "version": recipe.version,
            "is_active": recipe.is_active,
            "notes": recipe.notes,
            "created_at": recipe.created_at,
            "updated_at": recipe.updated_at,
            "items": recipe_items,
            "total_cost": total_cost
        }
    
    profit_margin = None
    if hpp and hpp > 0:
        profit_margin = ((Decimal(str(result.price)) - hpp) / Decimal(str(result.price))) * 100
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "name": result.name,
        "category": result.category,
        "price": result.price,
        "description": result.description,
        "image_url": result.image_url,
        "is_active": result.is_active,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "active_recipe": active_recipe,
        "hpp": hpp,
        "profit_margin": profit_margin
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_menu(
    data: MenuCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Create new menu with optional recipe"""
    
    # Check menu limit
    org = db.execute(
        text("SELECT max_menu_items FROM organizations WHERE id = :org_id"),
        {"org_id": str(organization_id)}
    ).fetchone()
    
    current_count = db.execute(
        text("SELECT COUNT(*) as count FROM menus WHERE organization_id = :org_id"),
        {"org_id": str(organization_id)}
    ).fetchone().count
    
    if current_count >= org.max_menu_items:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Menu limit reached. Maximum {org.max_menu_items} menus allowed for your plan."
        )
    
    # Insert menu
    menu_result = db.execute(
        text("""
            INSERT INTO menus 
            (organization_id, name, category, price, description, image_url, is_active)
            VALUES (:org_id, :name, :category, :price, :description, :image_url, true)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "name": data.name,
            "category": data.category,
            "price": float(data.price),
            "description": data.description,
            "image_url": data.image_url
        }
    ).fetchone()
    
    menu_id = menu_result.id
    
    # Create recipe if provided
    if data.recipe:
        recipe_result = db.execute(
            text("""
                INSERT INTO recipes
                (menu_id, version, is_active, notes)
                VALUES (:menu_id, :version, true, :notes)
                RETURNING id
            """),
            {
                "menu_id": menu_id,
                "version": data.recipe.version,
                "notes": data.recipe.notes
            }
        ).fetchone()
        
        recipe_id = recipe_result.id
        
        # Insert recipe items
        for item in data.recipe.items:
            db.execute(
                text("""
                    INSERT INTO recipe_items
                    (recipe_id, ingredient_id, qty, unit_id)
                    VALUES (:recipe_id, :ingredient_id, :qty, :unit_id)
                """),
                {
                    "recipe_id": recipe_id,
                    "ingredient_id": str(item.ingredient_id),
                    "qty": float(item.qty),
                    "unit_id": str(item.unit_id)
                }
            )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Menu created",
        "menu_id": str(menu_id)
    }


@router.patch("/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: UUID,
    data: MenuUpdate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER"))
):
    """Update menu"""
    
    existing = db.execute(
        text("SELECT id FROM menus WHERE id = :menu_id AND organization_id = :org_id"),
        {"menu_id": str(menu_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    update_fields = []
    params = {"menu_id": str(menu_id), "org_id": str(organization_id)}
    
    if data.name is not None:
        update_fields.append("name = :name")
        params["name"] = data.name
    
    if data.category is not None:
        update_fields.append("category = :category")
        params["category"] = data.category
    
    if data.price is not None:
        update_fields.append("price = :price")
        params["price"] = float(data.price)
    
    if data.description is not None:
        update_fields.append("description = :description")
        params["description"] = data.description
    
    if data.image_url is not None:
        update_fields.append("image_url = :image_url")
        params["image_url"] = data.image_url
    
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
        UPDATE menus
        SET {', '.join(update_fields)}
        WHERE id = :menu_id AND organization_id = :org_id
    """
    
    db.execute(text(query), params)
    db.commit()
    
    # Return updated menu
    return get_menu_by_id(menu_id, organization_id, db, current_user)


@router.post("/{menu_id}/recipes", status_code=status.HTTP_201_CREATED)
def create_recipe_for_menu(
    menu_id: UUID,
    data: RecipeCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER"))
):
    """Create new recipe version for menu"""
    
    # Verify menu exists
    menu = db.execute(
        text("SELECT id FROM menus WHERE id = :menu_id AND organization_id = :org_id"),
        {"menu_id": str(menu_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    # Get max version
    max_version = db.execute(
        text("SELECT COALESCE(MAX(version), 0) as max_version FROM recipes WHERE menu_id = :menu_id"),
        {"menu_id": str(menu_id)}
    ).fetchone().max_version
    
    new_version = max_version + 1
    
    # Deactivate old recipes if this one is active
    if data.is_active:
        db.execute(
            text("UPDATE recipes SET is_active = false WHERE menu_id = :menu_id"),
            {"menu_id": str(menu_id)}
        )
    
    # Insert new recipe
    recipe_result = db.execute(
        text("""
            INSERT INTO recipes
            (menu_id, version, is_active, notes)
            VALUES (:menu_id, :version, :is_active, :notes)
            RETURNING id
        """),
        {
            "menu_id": str(menu_id),
            "version": new_version,
            "is_active": data.is_active,
            "notes": data.notes
        }
    ).fetchone()
    
    recipe_id = recipe_result.id
    
    # Insert recipe items
    for item in data.items:
        db.execute(
            text("""
                INSERT INTO recipe_items
                (recipe_id, ingredient_id, qty, unit_id)
                VALUES (:recipe_id, :ingredient_id, :qty, :unit_id)
            """),
            {
                "recipe_id": recipe_id,
                "ingredient_id": str(item.ingredient_id),
                "qty": float(item.qty),
                "unit_id": str(item.unit_id)
            }
        )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Recipe created",
        "recipe_id": str(recipe_id),
        "version": new_version
    }


@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN"))
):
    """Delete menu (soft delete)"""
    
    existing = db.execute(
        text("SELECT id FROM menus WHERE id = :menu_id AND organization_id = :org_id"),
        {"menu_id": str(menu_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    db.execute(
        text("UPDATE menus SET is_active = false, updated_at = NOW() WHERE id = :menu_id"),
        {"menu_id": str(menu_id)}
    )
    
    db.commit()
    
    return None