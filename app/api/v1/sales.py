from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
import json

from app.database import get_db
from app.dependencies import get_current_user, require_role, get_organization_context
from app.schemas.sales import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderItemResponse,
    MenuEngineeringItem
)

router = APIRouter()


def generate_order_number(organization_id: str, outlet_id: str, db: Session) -> str:
    """Generate unique order number"""
    today = date.today()
    
    # Get outlet code
    outlet = db.execute(
        text("SELECT code FROM outlets WHERE id = :outlet_id"),
        {"outlet_id": outlet_id}
    ).fetchone()
    
    outlet_code = outlet.code if outlet else "OUT"
    prefix = f"{outlet_code}-{today.strftime('%Y%m%d')}"
    
    count = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM sales_orders
            WHERE organization_id = :org_id
            AND outlet_id = :outlet_id
            AND DATE(order_datetime) = :today
        """),
        {"org_id": organization_id, "outlet_id": outlet_id, "today": today}
    ).fetchone().count
    
    return f"{prefix}-{count + 1:04d}"


@router.get("/", response_model=List[SalesOrderResponse])
def get_all_sales_orders(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, le=1000, description="Limit results"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all sales orders"""
    
    query = """
        SELECT 
            so.id, so.organization_id, so.order_no, so.outlet_id, so.user_id,
            so.order_datetime, so.total_amount, so.payment_method, 
            so.customer_name, so.notes, so.created_at,
            o.name as outlet_name,
            u.name as cashier_name
        FROM sales_orders so
        JOIN outlets o ON o.id = so.outlet_id
        JOIN users u ON u.id = so.user_id
        WHERE so.organization_id = :org_id
    """
    
    params = {"org_id": str(organization_id)}
    
    if outlet_id:
        query += " AND so.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    if start_date:
        query += " AND so.order_datetime >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND so.order_datetime <= :end_date"
        params["end_date"] = end_date
    
    query += " ORDER BY so.order_datetime DESC LIMIT :limit"
    params["limit"] = limit
    
    results = db.execute(text(query), params).fetchall()
    
    # Get items for each order
    orders = []
    for r in results:
        items = db.execute(
            text("""
                SELECT 
                    soi.id, soi.sales_order_id, soi.menu_id, soi.qty,
                    soi.price_at_that_time, soi.hpp_at_that_time, soi.total_item_amount,
                    soi.ingredient_usage_json, soi.modifier_json, soi.notes,
                    m.name as menu_name
                FROM sales_order_items soi
                JOIN menus m ON m.id = soi.menu_id
                WHERE soi.sales_order_id = :order_id
            """),
            {"order_id": r.id}
        ).fetchall()
        
        orders.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "order_no": r.order_no,
            "outlet_id": r.outlet_id,
            "user_id": r.user_id,
            "order_datetime": r.order_datetime,
            "total_amount": r.total_amount,
            "payment_method": r.payment_method,
            "customer_name": r.customer_name,
            "notes": r.notes,
            "created_at": r.created_at,
            "outlet_name": r.outlet_name,
            "cashier_name": r.cashier_name,
            "items": [
                {
                    "id": item.id,
                    "sales_order_id": item.sales_order_id,
                    "menu_id": item.menu_id,
                    "qty": item.qty,
                    "price_at_that_time": item.price_at_that_time,
                    "hpp_at_that_time": item.hpp_at_that_time,
                    "total_item_amount": item.total_item_amount,
                    "ingredient_usage_json": json.loads(item.ingredient_usage_json) if item.ingredient_usage_json else None,
                    "modifier_json": json.loads(item.modifier_json) if item.modifier_json else None,
                    "notes": item.notes,
                    "menu_name": item.menu_name
                }
                for item in items
            ]
        })
    
    return orders


@router.get("/{order_id}", response_model=SalesOrderResponse)
def get_sales_order_by_id(
    order_id: UUID,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get sales order by ID"""
    
    result = db.execute(
        text("""
            SELECT 
                so.id, so.organization_id, so.order_no, so.outlet_id, so.user_id,
                so.order_datetime, so.total_amount, so.payment_method, 
                so.customer_name, so.notes, so.created_at,
                o.name as outlet_name,
                u.name as cashier_name
            FROM sales_orders so
            JOIN outlets o ON o.id = so.outlet_id
            JOIN users u ON u.id = so.user_id
            WHERE so.id = :order_id AND so.organization_id = :org_id
        """),
        {"order_id": str(order_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found"
        )
    
    items = db.execute(
        text("""
            SELECT 
                soi.id, soi.sales_order_id, soi.menu_id, soi.qty,
                soi.price_at_that_time, soi.hpp_at_that_time, soi.total_item_amount,
                soi.ingredient_usage_json, soi.modifier_json, soi.notes,
                m.name as menu_name
            FROM sales_order_items soi
            JOIN menus m ON m.id = soi.menu_id
            WHERE soi.sales_order_id = :order_id
        """),
        {"order_id": str(order_id)}
    ).fetchall()
    
    return {
        "id": result.id,
        "organization_id": result.organization_id,
        "order_no": result.order_no,
        "outlet_id": result.outlet_id,
        "user_id": result.user_id,
        "order_datetime": result.order_datetime,
        "total_amount": result.total_amount,
        "payment_method": result.payment_method,
        "customer_name": result.customer_name,
        "notes": result.notes,
        "created_at": result.created_at,
        "outlet_name": result.outlet_name,
        "cashier_name": result.cashier_name,
        "items": [
            {
                "id": item.id,
                "sales_order_id": item.sales_order_id,
                "menu_id": item.menu_id,
                "qty": item.qty,
                "price_at_that_time": item.price_at_that_time,
                "hpp_at_that_time": item.hpp_at_that_time,
                "total_item_amount": item.total_item_amount,
                "ingredient_usage_json": json.loads(item.ingredient_usage_json) if item.ingredient_usage_json else None,
                "modifier_json": json.loads(item.modifier_json) if item.modifier_json else None,
                "notes": item.notes,
                "menu_name": item.menu_name
            }
            for item in items
        ]
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_sales_order(
    data: SalesOrderCreate,
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("OWNER", "ADMIN", "CENTRAL_MANAGER", "OUTLET_MANAGER", "CASHIER"))
):
    """Create new sales order (POS transaction)"""
    
    # Verify outlet
    outlet = db.execute(
        text("SELECT id FROM outlets WHERE id = :outlet_id AND organization_id = :org_id"),
        {"outlet_id": str(data.outlet_id), "org_id": str(organization_id)}
    ).fetchone()
    
    if not outlet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlet not found"
        )
    
    # Generate order number
    order_no = generate_order_number(str(organization_id), str(data.outlet_id), db)
    
    # Calculate total and prepare items
    total_amount = Decimal(0)
    order_items = []
    
    for item_data in data.items:
        # Get menu details and active recipe
        menu = db.execute(
            text("""
                SELECT m.id, m.name, m.price, m.is_active
                FROM menus m
                WHERE m.id = :menu_id AND m.organization_id = :org_id
            """),
            {"menu_id": str(item_data.menu_id), "org_id": str(organization_id)}
        ).fetchone()
        
        if not menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu {item_data.menu_id} not found"
            )
        
        if not menu.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu '{menu.name}' is not active"
            )
        
        # Get active recipe
        recipe = db.execute(
            text("""
                SELECT id FROM recipes
                WHERE menu_id = :menu_id AND is_active = true
                ORDER BY version DESC
                LIMIT 1
            """),
            {"menu_id": str(item_data.menu_id)}
        ).fetchone()
        
        # Get recipe items (ingredients)
        ingredient_usage = []
        total_hpp = Decimal(0)
        
        if recipe:
            recipe_items = db.execute(
                text("""
                    SELECT 
                        ri.ingredient_id, ri.qty, ri.unit_id,
                        i.name as ingredient_name,
                        u.symbol as unit_symbol,
                        s.last_cost
                    FROM recipe_items ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    JOIN units u ON u.id = ri.unit_id
                    LEFT JOIN inventory_stock s ON s.ingredient_id = ri.ingredient_id 
                        AND s.outlet_id = :outlet_id
                    WHERE ri.recipe_id = :recipe_id
                """),
                {"recipe_id": recipe.id, "outlet_id": str(data.outlet_id)}
            ).fetchall()
            
            for ri in recipe_items:
                usage_qty = Decimal(str(ri.qty)) * item_data.qty
                item_cost = Decimal(0)
                
                if ri.last_cost:
                    item_cost = usage_qty * Decimal(str(ri.last_cost))
                    total_hpp += item_cost
                
                ingredient_usage.append({
                    "ingredient_id": str(ri.ingredient_id),
                    "ingredient_name": ri.ingredient_name,
                    "qty": float(usage_qty),
                    "unit_id": str(ri.unit_id),
                    "unit_symbol": ri.unit_symbol,
                    "unit_cost": float(ri.last_cost) if ri.last_cost else 0,
                    "total_cost": float(item_cost)
                })
                
                # Check stock availability
                stock = db.execute(
                    text("""
                        SELECT qty_on_hand
                        FROM inventory_stock
                        WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
                    """),
                    {"outlet_id": str(data.outlet_id), "ingredient_id": ri.ingredient_id}
                ).fetchone()
                
                if not stock or float(stock.qty_on_hand) < float(usage_qty):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for ingredient '{ri.ingredient_name}'"
                    )
        
        # Calculate item total
        item_total = Decimal(str(menu.price)) * item_data.qty
        total_amount += item_total
        
        order_items.append({
            "menu_id": str(item_data.menu_id),
            "qty": item_data.qty,
            "price": Decimal(str(menu.price)),
            "hpp": total_hpp / item_data.qty if item_data.qty > 0 else Decimal(0),
            "total": item_total,
            "ingredient_usage": ingredient_usage,
            "notes": item_data.notes
        })
    
    # Insert sales order
    order_result = db.execute(
        text("""
            INSERT INTO sales_orders
            (organization_id, order_no, outlet_id, user_id, order_datetime,
             total_amount, payment_method, customer_name, notes)
            VALUES (:org_id, :order_no, :outlet_id, :user_id, NOW(),
                    :total_amount, :payment_method, :customer_name, :notes)
            RETURNING id
        """),
        {
            "org_id": str(organization_id),
            "order_no": order_no,
            "outlet_id": str(data.outlet_id),
            "user_id": current_user["user_id"],
            "total_amount": float(total_amount),
            "payment_method": data.payment_method,
            "customer_name": data.customer_name,
            "notes": data.notes
        }
    ).fetchone()
    
    order_id = order_result.id
    
    # Insert order items and update inventory
    for item in order_items:
        # Insert order item
        db.execute(
            text("""
                INSERT INTO sales_order_items
                (sales_order_id, menu_id, qty, price_at_that_time, hpp_at_that_time,
                 total_item_amount, ingredient_usage_json, notes)
                VALUES (:order_id, :menu_id, :qty, :price, :hpp,
                        :total, :ingredient_usage::jsonb, :notes)
            """),
            {
                "order_id": order_id,
                "menu_id": item["menu_id"],
                "qty": item["qty"],
                "price": float(item["price"]),
                "hpp": float(item["hpp"]),
                "total": float(item["total"]),
                "ingredient_usage": json.dumps(item["ingredient_usage"]),
                "notes": item["notes"]
            }
        )
        
        # Update inventory and create ledger entries
        for ingredient in item["ingredient_usage"]:
            # Update stock
            db.execute(
                text("""
                    UPDATE inventory_stock
                    SET qty_on_hand = qty_on_hand - :usage_qty,
                        updated_at = NOW()
                    WHERE outlet_id = :outlet_id AND ingredient_id = :ingredient_id
                """),
                {
                    "usage_qty": ingredient["qty"],
                    "outlet_id": str(data.outlet_id),
                    "ingredient_id": ingredient["ingredient_id"]
                }
            )
            
            # Create ledger entry
            db.execute(
                text("""
                    INSERT INTO inventory_ledger
                    (organization_id, outlet_id, ingredient_id, change_qty,
                     source_type, source_id, unit_id, unit_cost, total_cost,
                     remarks)
                    VALUES (:org_id, :outlet_id, :ingredient_id, :change_qty,
                            'SALE', :source_id, :unit_id, :unit_cost, :total_cost,
                            :remarks)
                """),
                {
                    "org_id": str(organization_id),
                    "outlet_id": str(data.outlet_id),
                    "ingredient_id": ingredient["ingredient_id"],
                    "change_qty": -float(ingredient["qty"]),
                    "source_id": order_id,
                    "unit_id": ingredient["unit_id"],
                    "unit_cost": ingredient["unit_cost"],
                    "total_cost": ingredient["total_cost"],
                    "remarks": f"Sold via order {order_no}"
                }
            )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Sales order created",
        "order_id": str(order_id),
        "order_no": order_no,
        "total_amount": float(total_amount)
    }


@router.get("/reports/daily-summary")
def get_daily_sales_summary(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    report_date: date = Query(default=date.today(), description="Report date"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get daily sales summary"""
    
    query = """
        SELECT 
            COUNT(*) as total_transactions,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_transaction,
            MAX(total_amount) as max_transaction,
            MIN(total_amount) as min_transaction
        FROM sales_orders
        WHERE organization_id = :org_id
        AND DATE(order_datetime) = :report_date
    """
    
    params = {"org_id": str(organization_id), "report_date": report_date}
    
    if outlet_id:
        query += " AND outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    summary = db.execute(text(query), params).fetchone()
    
    # Get top selling items
    top_items_query = """
        SELECT 
            m.name as menu_name,
            SUM(soi.qty) as total_qty_sold,
            SUM(soi.total_item_amount) as total_revenue
        FROM sales_order_items soi
        JOIN sales_orders so ON so.id = soi.sales_order_id
        JOIN menus m ON m.id = soi.menu_id
        WHERE so.organization_id = :org_id
        AND DATE(so.order_datetime) = :report_date
    """
    
    if outlet_id:
        top_items_query += " AND so.outlet_id = :outlet_id"
    
    top_items_query += """
        GROUP BY m.id, m.name
        ORDER BY total_qty_sold DESC
        LIMIT 10
    """
    
    top_items = db.execute(text(top_items_query), params).fetchall()
    
    return {
        "date": report_date,
        "summary": {
            "total_transactions": summary.total_transactions or 0,
            "total_revenue": float(summary.total_revenue) if summary.total_revenue else 0,
            "avg_transaction": float(summary.avg_transaction) if summary.avg_transaction else 0,
            "max_transaction": float(summary.max_transaction) if summary.max_transaction else 0,
            "min_transaction": float(summary.min_transaction) if summary.min_transaction else 0
        },
        "top_selling_items": [
            {
                "menu_name": item.menu_name,
                "total_qty_sold": item.total_qty_sold,
                "total_revenue": float(item.total_revenue)
            }
            for item in top_items
        ]
    }


@router.get("/reports/menu-engineering", response_model=List[MenuEngineeringItem])
def get_menu_engineering_report(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Menu Engineering analytics
    Classifies menus into: STAR, PLOWHORSE, PUZZLE, DOG
    Based on popularity and profitability
    """
    
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        from datetime import timedelta
        start_date = end_date - timedelta(days=30)
    
    query = """
        SELECT 
            m.id as menu_id,
            m.name as menu_name,
            m.category,
            COUNT(soi.id) as total_qty_sold,
            SUM(soi.total_item_amount) as total_revenue,
            AVG(soi.price_at_that_time) as avg_price,
            SUM(soi.hpp_at_that_time * soi.qty) as total_cost,
            SUM(soi.total_item_amount - (soi.hpp_at_that_time * soi.qty)) as total_profit
        FROM sales_order_items soi
        JOIN sales_orders so ON so.id = soi.sales_order_id
        JOIN menus m ON m.id = soi.menu_id
        WHERE so.organization_id = :org_id
        AND so.order_datetime >= :start_date
        AND so.order_datetime <= :end_date
    """
    
    params = {
        "org_id": str(organization_id),
        "start_date": start_date,
        "end_date": end_date
    }
    
    if outlet_id:
        query += " AND so.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    query += """
        GROUP BY m.id, m.name, m.category
        HAVING COUNT(soi.id) > 0
    """
    
    results = db.execute(text(query), params).fetchall()
    
    if not results:
        return []
    
    # Calculate averages for classification
    total_qty = sum(r.total_qty_sold for r in results)
    avg_qty_sold = total_qty / len(results) if len(results) > 0 else 0
    
    menu_items = []
    profit_margins = []
    
    for r in results:
        profit_margin = ((float(r.total_revenue) - float(r.total_cost)) / float(r.total_revenue) * 100) if r.total_revenue > 0 else 0
        profit_margins.append(profit_margin)
        
        menu_items.append({
            "menu_id": r.menu_id,
            "menu_name": r.menu_name,
            "category": r.category,
            "total_qty_sold": r.total_qty_sold,
            "total_revenue": r.total_revenue,
            "avg_price": r.avg_price,
            "total_cost": r.total_cost,
            "total_profit": r.total_profit,
            "profit_margin": profit_margin,
            "popularity_score": r.total_qty_sold / avg_qty_sold if avg_qty_sold > 0 else 0,
            "profitability_score": 0  # Will calculate below
        })
    
    avg_profit_margin = sum(profit_margins) / len(profit_margins) if len(profit_margins) > 0 else 0
    
    # Classify each menu item
    result_items = []
    for item in menu_items:
        # Profitability score (compared to average)
        profitability_score = item["profit_margin"] / avg_profit_margin if avg_profit_margin > 0 else 0
        item["profitability_score"] = profitability_score
        
        # Classification
        is_popular = item["popularity_score"] >= 1.0  # Above average
        is_profitable = profitability_score >= 1.0  # Above average
        
        if is_popular and is_profitable:
            classification = "STAR"  # High popularity, high profit
        elif is_popular and not is_profitable:
            classification = "PLOWHORSE"  # High popularity, low profit
        elif not is_popular and is_profitable:
            classification = "PUZZLE"  # Low popularity, high profit
        else:
            classification = "DOG"  # Low popularity, low profit
        
        result_items.append({
            "menu_id": str(item["menu_id"]),
            "menu_name": item["menu_name"],
            "category": item["category"],
            "total_qty_sold": item["total_qty_sold"],
            "total_revenue": float(item["total_revenue"]),
            "avg_price": float(item["avg_price"]),
            "total_cost": float(item["total_cost"]),
            "total_profit": float(item["total_profit"]),
            "profit_margin": item["profit_margin"],
            "popularity_score": item["popularity_score"],
            "profitability_score": profitability_score,
            "classification": classification
        })
    
    # Sort by classification priority (STAR > PLOWHORSE > PUZZLE > DOG)
    classification_order = {"STAR": 0, "PLOWHORSE": 1, "PUZZLE": 2, "DOG": 3}
    result_items.sort(key=lambda x: (classification_order.get(x["classification"], 4), -x["total_qty_sold"]))
    
    return result_items