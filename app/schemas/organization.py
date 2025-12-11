from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class OrganizationBase(BaseModel):
    name: str
    slug: str
    phone: Optional[str] = None
    address: Optional[str] = None
    billing_email: Optional[EmailStr] = None


class OrganizationCreate(OrganizationBase):
    subscription_tier: str = "STARTER"


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    billing_email: Optional[EmailStr] = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    subscription_tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    max_outlets: int
    max_menu_items: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True