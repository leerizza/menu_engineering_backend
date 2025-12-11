from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class RecipeItemBase(BaseModel):
    ingredient_id: UUID
    qty: Decimal
    unit_id: UUID


class RecipeItemCreate(RecipeItemBase):
    pass


class RecipeItemResponse(RecipeItemBase):
    id: UUID
    recipe_id: UUID
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    ingredient_cost: Optional[Decimal] = None
    
    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    version: int = 1
    is_active: bool = True
    notes: Optional[str] = None


class RecipeCreate(RecipeBase):
    items: List[RecipeItemCreate]


class RecipeUpdate(BaseModel):
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class RecipeResponse(RecipeBase):
    id: UUID
    menu_id: UUID
    created_at: datetime
    updated_at: datetime
    items: List[RecipeItemResponse] = []
    total_cost: Optional[Decimal] = None
    
    class Config:
        from_attributes = True


class MenuBase(BaseModel):
    name: str
    category: Optional[str] = None
    price: Decimal
    description: Optional[str] = None
    image_url: Optional[str] = None


class MenuCreate(MenuBase):
    recipe: Optional[RecipeCreate] = None


class MenuUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class MenuResponse(MenuBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    active_recipe: Optional[RecipeResponse] = None
    hpp: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    
    class Config:
        from_attributes = True