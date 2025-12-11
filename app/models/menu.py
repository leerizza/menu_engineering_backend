from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class Menu(Base, TimestampMixin):
    __tablename__ = "menus"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    price = Column(Numeric(12, 2), nullable=False)
    description = Column(String)
    image_url = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="menus")
    recipes = relationship("Recipe", back_populates="menu", cascade="all, delete-orphan")


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id = Column(UUID(as_uuid=True), ForeignKey('menus.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(String)
    
    # Relationships
    menu = relationship("Menu", back_populates="recipes")
    items = relationship("RecipeItem", back_populates="recipe", cascade="all, delete-orphan")


class RecipeItem(Base):
    __tablename__ = "recipe_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id'), nullable=False)
    qty = Column(Numeric(12, 4), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="items")
    ingredient = relationship("Ingredient", back_populates="recipe_items")
    unit = relationship("Unit")