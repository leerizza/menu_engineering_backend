from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    subscription_tier = Column(String(50), nullable=False, default='STARTER')
    subscription_status = Column(String(50), nullable=False, default='TRIAL')
    trial_ends_at = Column(DateTime(timezone=True))
    billing_email = Column(String(255))
    max_outlets = Column(Integer, nullable=False, default=1)
    max_menu_items = Column(Integer, nullable=False, default=50)
    phone = Column(String(50))
    address = Column(String)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    outlets = relationship("Outlet", back_populates="organization")
    ingredients = relationship("Ingredient", back_populates="organization")
    suppliers = relationship("Supplier", back_populates="organization")
    menus = relationship("Menu", back_populates="organization")