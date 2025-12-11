from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class Ingredient(Base, TimestampMixin):
    __tablename__ = "ingredients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    sku = Column(String(100))
    base_unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="ingredients")
    base_unit = relationship("Unit", foreign_keys=[base_unit_id])
    inventory_stocks = relationship("InventoryStock", back_populates="ingredient")
    recipe_items = relationship("RecipeItem", back_populates="ingredient")