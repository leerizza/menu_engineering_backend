from sqlalchemy import Column, String, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class StockRequest(Base, TimestampMixin):
    __tablename__ = "stock_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    request_no = Column(String(100), nullable=False)
    from_outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    to_outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    status = Column(String(50), nullable=False, default='PENDING')  # PENDING, APPROVED, REJECTED, FULFILLED, CANCELLED
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    notes = Column(String)
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    from_outlet = relationship("Outlet", foreign_keys=[from_outlet_id])
    to_outlet = relationship("Outlet", foreign_keys=[to_outlet_id])
    items = relationship("StockRequestItem", back_populates="stock_request", cascade="all, delete-orphan")


class StockRequestItem(Base):
    __tablename__ = "stock_request_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_request_id = Column(UUID(as_uuid=True), ForeignKey('stock_requests.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id'), nullable=False)
    requested_qty = Column(Numeric(12, 4), nullable=False)
    requested_unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    approved_qty = Column(Numeric(12, 4), default=0)
    notes = Column(String)
    
    # Relationships
    stock_request = relationship("StockRequest", back_populates="items")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")