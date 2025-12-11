from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Date, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    plan = Column(String(50), nullable=False)  # STARTER, PRO, ENTERPRISE
    status = Column(String(50), nullable=False, default='ACTIVE')  # ACTIVE, CANCELLED, PAST_DUE
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)


class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.id'))
    invoice_no = Column(String(100), unique=True, nullable=False)
    amount_due = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), nullable=False, default='UNPAID')  # PAID, UNPAID, VOID
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime(timezone=True))
    payment_method = Column(String(50))
    payment_reference = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default='now()')


class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    metric_type = Column(String(50), nullable=False)  # OUTLETS, MENU_ITEMS, TRANSACTIONS
    current_count = Column(Integer, nullable=False)
    limit_count = Column(Integer, nullable=False)
    tracked_at = Column(DateTime(timezone=True), server_default='now()', nullable=False)