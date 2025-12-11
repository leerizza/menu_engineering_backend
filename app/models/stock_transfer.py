from sqlalchemy import Column, String, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class StockTransfer(Base, TimestampMixin):
    __tablename__ = "stock_transfers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    transfer_no = Column(String(100), nullable=False)
    from_outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    to_outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    stock_request_id = Column(UUID(as_uuid=True), ForeignKey('stock_requests.id'))
    status = Column(String(50), nullable=False, default='DRAFT')  # DRAFT, SHIPPED, RECEIVED, CANCELLED
    shipped_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    received_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    notes = Column(String)
    
    # Relationships
    from_outlet = relationship("Outlet", foreign_keys=[from_outlet_id])
    to_outlet = relationship("Outlet", foreign_keys=[to_outlet_id])
    stock_request = relationship("StockRequest")
    items = relationship("StockTransferItem", back_populates="stock_transfer", cascade="all, delete-orphan")


class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_transfer_id = Column(UUID(as_uuid=True), ForeignKey('stock_transfers.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id'), nullable=False)
    qty = Column(Numeric(12, 4), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    unit_cost = Column(Numeric(12, 2))
    total_cost = Column(Numeric(12, 2))
    
    # Relationships
    stock_transfer = relationship("StockTransfer", back_populates="items")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")