from sqlalchemy import Column, String, ForeignKey, DateTime, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    po_no = Column(String(100), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    status = Column(String(50), nullable=False, default='DRAFT')  # DRAFT, ORDERED, RECEIVED, CANCELLED
    order_date = Column(Date, nullable=False)
    expected_date = Column(Date)
    received_date = Column(Date)
    total_amount = Column(Numeric(12, 2))
    notes = Column(String)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    received_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    outlet = relationship("Outlet")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id'), nullable=False)
    qty_ordered = Column(Numeric(12, 4), nullable=False)
    qty_received = Column(Numeric(12, 4), default=0)
    unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    total_cost = Column(Numeric(12, 2), nullable=False)
    notes = Column(String)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")