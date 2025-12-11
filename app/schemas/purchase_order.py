from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


class PurchaseOrderItemBase(BaseModel):
    ingredient_id: UUID
    qty_ordered: Decimal
    unit_id: UUID
    unit_cost: Decimal
    notes: Optional[str] = None


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass


class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    id: UUID
    purchase_order_id: UUID
    qty_received: Decimal
    total_cost: Decimal
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    
    class Config:
        from_attributes = True


class PurchaseOrderBase(BaseModel):
    supplier_id: UUID
    outlet_id: UUID
    order_date: date
    expected_date: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    id: UUID
    organization_id: UUID
    po_no: str
    status: str
    received_date: Optional[date]
    total_amount: Optional[Decimal]
    created_by: Optional[UUID]
    received_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    supplier_name: Optional[str]
    outlet_name: Optional[str]
    items: List[PurchaseOrderItemResponse] = []
    
    class Config:
        from_attributes = True


class ReceivePurchaseOrderItem(BaseModel):
    item_id: UUID
    qty_received: Decimal


class ReceivePurchaseOrder(BaseModel):
    items: List[ReceivePurchaseOrderItem]
    received_date: date