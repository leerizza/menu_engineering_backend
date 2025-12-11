from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class Outlet(Base, TimestampMixin):
    __tablename__ = "outlets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)  # CENTRAL or OUTLET
    address = Column(String)
    phone = Column(String(50))
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="outlets")
    inventory_stocks = relationship("InventoryStock", back_populates="outlet")