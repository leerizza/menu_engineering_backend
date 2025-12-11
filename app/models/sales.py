from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    order_no = Column(String(100), nullable=False)
    outlet_id = Column(UUID(as_uuid=True), ForeignKey('outlets.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    order_datetime = Column(DateTime(timezone=True), server_default='now()', nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50))
    customer_name = Column(String(255))
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    
    # Relationships
    outlet = relationship("Outlet")
    user = relationship("User")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False)
    menu_id = Column(UUID(as_uuid=True), ForeignKey('menus.id'), nullable=False)
    qty = Column(Integer, nullable=False)
    price_at_that_time = Column(Numeric(12, 2), nullable=False)
    hpp_at_that_time = Column(Numeric(12, 2))
    total_item_amount = Column(Numeric(12, 2), nullable=False)
    ingredient_usage_json = Column(JSONB)  # Snapshot of ingredients used
    modifier_json = Column(JSONB)  # Any modifications
    notes = Column(String)
    
    # Relationships
    sales_order = relationship("SalesOrder", back_populates="items")
    menu = relationship("Menu")