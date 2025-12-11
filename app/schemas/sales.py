from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class SalesOrderItemBase(BaseModel):
    menu_id: UUID
    qty: int
    notes: Optional[str] = None


class SalesOrderItemCreate(SalesOrderItemBase):
    pass


class SalesOrderItemResponse(SalesOrderItemBase):
    id: UUID
    sales_order_id: UUID
    price_at_that_time: Decimal
    hpp_at_that_time: Optional[Decimal]
    total_item_amount: Decimal
    ingredient_usage_json: Optional[dict]
    modifier_json: Optional[dict]
    menu_name: Optional[str]
    
    class Config:
        from_attributes = True


class SalesOrderBase(BaseModel):
    outlet_id: UUID
    payment_method: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None


class SalesOrderCreate(SalesOrderBase):
    items: List[SalesOrderItemCreate]


class SalesOrderResponse(SalesOrderBase):
    id: UUID
    organization_id: UUID
    order_no: str
    user_id: UUID
    order_datetime: datetime
    total_amount: Decimal
    created_at: datetime
    
    # Additional fields
    outlet_name: Optional[str]
    cashier_name: Optional[str]
    items: List[SalesOrderItemResponse] = []
    
    class Config:
        from_attributes = True


class SalesReportParams(BaseModel):
    outlet_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class MenuEngineeringItem(BaseModel):
    menu_id: UUID
    menu_name: str
    category: Optional[str]
    total_qty_sold: int
    total_revenue: Decimal
    avg_price: Decimal
    total_cost: Decimal
    total_profit: Decimal
    profit_margin: Decimal
    popularity_score: float
    profitability_score: float
    classification: str  # STAR, PLOWHORSE, PUZZLE, DOG