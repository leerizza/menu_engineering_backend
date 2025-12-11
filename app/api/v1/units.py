from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.unit import UnitResponse, UnitConversionResponse

router = APIRouter()


@router.get("/", response_model=List[UnitResponse])
def get_all_units(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all units (global, no org filter)"""
    
    results = db.execute(
        text("""
            SELECT id, name, symbol, is_base_unit, created_at
            FROM units
            ORDER BY name ASC
        """)
    ).fetchall()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "symbol": r.symbol,
            "is_base_unit": r.is_base_unit,
            "created_at": r.created_at
        }
        for r in results
    ]


@router.get("/conversions", response_model=List[UnitConversionResponse])
def get_unit_conversions(
    ingredient_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get unit conversions"""
    
    query = """
        SELECT 
            uc.id, uc.ingredient_id, uc.from_unit_id, uc.to_unit_id, 
            uc.multiplier, uc.created_at,
            u1.symbol as from_unit_symbol,
            u2.symbol as to_unit_symbol
        FROM unit_conversions uc
        LEFT JOIN units u1 ON u1.id = uc.from_unit_id
        LEFT JOIN units u2 ON u2.id = uc.to_unit_id
    """
    
    params = {}
    
    if ingredient_id:
        query += " WHERE (uc.ingredient_id = :ingredient_id OR uc.ingredient_id IS NULL)"
        params["ingredient_id"] = str(ingredient_id)
    
    query += " ORDER BY uc.created_at ASC"
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {
            "id": r.id,
            "ingredient_id": r.ingredient_id,
            "from_unit_id": r.from_unit_id,
            "to_unit_id": r.to_unit_id,
            "multiplier": float(r.multiplier),
            "from_unit_symbol": r.from_unit_symbol,
            "to_unit_symbol": r.to_unit_symbol,
            "created_at": r.created_at
        }
        for r in results
    ]


@router.post("/convert")
def convert_unit(
    from_unit_id: UUID,
    to_unit_id: UUID,
    quantity: float,
    ingredient_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Convert quantity from one unit to another"""
    
    # Try to find specific conversion for ingredient
    query = """
        SELECT multiplier 
        FROM unit_conversions
        WHERE from_unit_id = :from_unit_id 
        AND to_unit_id = :to_unit_id
    """
    params = {
        "from_unit_id": str(from_unit_id),
        "to_unit_id": str(to_unit_id)
    }
    
    if ingredient_id:
        query += " AND (ingredient_id = :ingredient_id OR ingredient_id IS NULL)"
        params["ingredient_id"] = str(ingredient_id)
        query += " ORDER BY ingredient_id DESC NULLS LAST LIMIT 1"
    else:
        query += " AND ingredient_id IS NULL"
    
    result = db.execute(text(query), params).fetchone()
    
    if not result:
        # Try reverse conversion
        reverse_query = """
            SELECT 1.0 / multiplier as multiplier
            FROM unit_conversions
            WHERE from_unit_id = :to_unit_id 
            AND to_unit_id = :from_unit_id
        """
        reverse_params = {
            "from_unit_id": str(to_unit_id),
            "to_unit_id": str(from_unit_id)
        }
        
        if ingredient_id:
            reverse_query += " AND (ingredient_id = :ingredient_id OR ingredient_id IS NULL)"
            reverse_params["ingredient_id"] = str(ingredient_id)
            reverse_query += " ORDER BY ingredient_id DESC NULLS LAST LIMIT 1"
        else:
            reverse_query += " AND ingredient_id IS NULL"
        
        result = db.execute(text(reverse_query), reverse_params).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No conversion found between these units"
        )
    
    converted_quantity = quantity * float(result.multiplier)
    
    return {
        "from_quantity": quantity,
        "to_quantity": converted_quantity,
        "multiplier": float(result.multiplier)
    }