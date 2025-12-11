from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Unit(Base):
    __tablename__ = "units"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    is_base_unit = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default='now()')


class UnitConversion(Base):
    __tablename__ = "unit_conversions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'))
    from_unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    to_unit_id = Column(UUID(as_uuid=True), ForeignKey('units.id'), nullable=False)
    multiplier = Column(String, nullable=False)  # Using String for NUMERIC
    created_at = Column(DateTime(timezone=True), server_default='now()')