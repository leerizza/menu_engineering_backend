from sqlalchemy import Column, String, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class InventoryStock(Base):
    __tablename__ = "inventory_stock"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    qty_on_hand = Column(Numeric(12, 4), nullable=False, default=0)
    min_qty = Column(Numeric(12, 4), nullable=False, default=0)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    last_cost = Column(Numeric(12, 2))
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')
    
    # Relationships
    outlet = relationship("Outlet", back_populates="inventory_stocks")
    ingredient = relationship("Ingredient", back_populates="inventory_stocks")
    unit = relationship("Unit")


class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    change_qty = Column(Numeric(12, 4), nullable=False)
    source_type = Column(String(50), nullable=False)  # PURCHASE, TRANSFER_IN, TRANSFER_OUT, SALE, ADJUSTMENT, WASTAGE
    source_id = Column(UUID(as_uuid=True))
    unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    unit_cost = Column(Numeric(12, 2))
    total_cost = Column(Numeric(12, 2))
    remarks = Column(String)
    created_at = Column(DateTime(timezone=True), server_default='now()')