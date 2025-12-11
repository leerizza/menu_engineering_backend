from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.database import get_db
from app.dependencies import get_current_user, get_organization_context

router = APIRouter()


@router.get("/dashboard-summary")
def get_dashboard_summary(
    outlet_id: Optional[UUID] = Query(None, description="Filter by specific outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive dashboard summary with key metrics:
    - Today's sales vs yesterday
    - This month vs last month
    - Top selling items
    - Low stock alerts
    - Recent transactions
    """
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    first_day_this_month = today.replace(day=1)
    last_month = (first_day_this_month - timedelta(days=1))
    first_day_last_month = last_month.replace(day=1)
    
    params = {"org_id": str(organization_id)}
    outlet_filter = ""
    
    if outlet_id:
        outlet_filter = " AND so.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    # Today's sales
    today_sales = db.execute(
        text(f"""
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total_amount), 0) as revenue,
                COALESCE(AVG(total_amount), 0) as avg_transaction
            FROM sales_orders so
            WHERE so.organization_id = :org_id
            AND DATE(so.order_datetime) = :today
            {outlet_filter}
        """),
        {**params, "today": today}
    ).fetchone()
    
    # Yesterday's sales
    yesterday_sales = db.execute(
        text(f"""
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total_amount), 0) as revenue
            FROM sales_orders so
            WHERE so.organization_id = :org_id
            AND DATE(so.order_datetime) = :yesterday
            {outlet_filter}
        """),
        {**params, "yesterday": yesterday}
    ).fetchone()
    
    # This month sales
    this_month_sales = db.execute(
        text(f"""
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total_amount), 0) as revenue,
                COALESCE(SUM(soi.hpp_at_that_time * soi.qty), 0) as total_cost
            FROM sales_orders so
            JOIN sales_order_items soi ON soi.sales_order_id = so.id
            WHERE so.organization_id = :org_id
            AND so.order_datetime >= :first_day
            AND so.order_datetime < :next_month
            {outlet_filter}
        """),
        {
            **params,
            "first_day": first_day_this_month,
            "next_month": first_day_this_month + timedelta(days=32)
        }
    ).fetchone()
    
    # Last month sales
    last_month_sales = db.execute(
        text(f"""
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total_amount), 0) as revenue
            FROM sales_orders so
            WHERE so.organization_id = :org_id
            AND so.order_datetime >= :first_day
            AND so.order_datetime < :last_day
            {outlet_filter}
        """),
        {
            **params,
            "first_day": first_day_last_month,
            "last_day": first_day_this_month
        }
    ).fetchone()
    
    # Top 5 selling items (last 30 days)
    top_items = db.execute(
        text(f"""
            SELECT 
                m.name as menu_name,
                m.category,
                SUM(soi.qty) as total_qty,
                SUM(soi.total_item_amount) as revenue
            FROM sales_order_items soi
            JOIN sales_orders so ON so.id = soi.sales_order_id
            JOIN menus m ON m.id = soi.menu_id
            WHERE so.organization_id = :org_id
            AND so.order_datetime >= :last_30_days
            {outlet_filter}
            GROUP BY m.id, m.name, m.category
            ORDER BY total_qty DESC
            LIMIT 5
        """),
        {**params, "last_30_days": today - timedelta(days=30)}
    ).fetchall()
    
    # Low stock alerts (items with qty < 10)
    low_stock = db.execute(
        text("""
            SELECT 
                i.name as ingredient_name,
                u.symbol as unit_symbol,
                s.qty_on_hand,
                o.name as outlet_name
            FROM inventory_stock s
            JOIN ingredients i ON i.id = s.ingredient_id
            JOIN units u ON u.id = s.unit_id
            JOIN outlets o ON o.id = s.outlet_id
            WHERE s.organization_id = :org_id
            AND s.qty_on_hand < 10
            ORDER BY s.qty_on_hand ASC
            LIMIT 10
        """),
        params
    ).fetchall()
    
    # Calculate growth percentages
    revenue_growth = 0
    if yesterday_sales.revenue > 0:
        revenue_growth = ((float(today_sales.revenue) - float(yesterday_sales.revenue)) / float(yesterday_sales.revenue)) * 100
    
    monthly_growth = 0
    if last_month_sales.revenue > 0:
        monthly_growth = ((float(this_month_sales.revenue) - float(last_month_sales.revenue)) / float(last_month_sales.revenue)) * 100
    
    # Calculate profit margin for this month
    month_profit_margin = 0
    if this_month_sales.revenue > 0:
        month_profit = float(this_month_sales.revenue) - float(this_month_sales.total_cost)
        month_profit_margin = (month_profit / float(this_month_sales.revenue)) * 100
    
    return {
        "today": {
            "transactions": today_sales.transactions,
            "revenue": float(today_sales.revenue),
            "avg_transaction": float(today_sales.avg_transaction),
            "growth_vs_yesterday": round(revenue_growth, 2)
        },
        "this_month": {
            "transactions": this_month_sales.transactions,
            "revenue": float(this_month_sales.revenue),
            "total_cost": float(this_month_sales.total_cost),
            "profit": float(this_month_sales.revenue) - float(this_month_sales.total_cost),
            "profit_margin": round(month_profit_margin, 2),
            "growth_vs_last_month": round(monthly_growth, 2)
        },
        "top_selling_items": [
            {
                "menu_name": item.menu_name,
                "category": item.category,
                "total_qty": item.total_qty,
                "revenue": float(item.revenue)
            }
            for item in top_items
        ],
        "low_stock_alerts": [
            {
                "ingredient_name": item.ingredient_name,
                "outlet_name": item.outlet_name,
                "qty_on_hand": float(item.qty_on_hand),
                "unit_symbol": item.unit_symbol,
                "status": "LOW" if item.qty_on_hand < 5 else "MEDIUM"
            }
            for item in low_stock
        ]
    }


@router.get("/sales-trend")
def get_sales_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get daily sales trend for chart visualization
    """
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        "org_id": str(organization_id),
        "start_date": start_date,
        "end_date": end_date
    }
    
    outlet_filter = ""
    if outlet_id:
        outlet_filter = " AND so.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    results = db.execute(
        text(f"""
            SELECT 
                DATE(so.order_datetime) as sale_date,
                COUNT(*) as transactions,
                COALESCE(SUM(so.total_amount), 0) as revenue,
                COALESCE(SUM(soi.hpp_at_that_time * soi.qty), 0) as cost,
                COALESCE(SUM(so.total_amount) - SUM(soi.hpp_at_that_time * soi.qty), 0) as profit
            FROM sales_orders so
            JOIN sales_order_items soi ON soi.sales_order_id = so.id
            WHERE so.organization_id = :org_id
            AND so.order_datetime >= :start_date
            AND so.order_datetime <= :end_date
            {outlet_filter}
            GROUP BY DATE(so.order_datetime)
            ORDER BY sale_date
        """),
        params
    ).fetchall()
    
    return {
        "period": {
            "start_date": start_date.date(),
            "end_date": end_date.date(),
            "days": days
        },
        "data": [
            {
                "date": str(r.sale_date),
                "transactions": r.transactions,
                "revenue": float(r.revenue),
                "cost": float(r.cost),
                "profit": float(r.profit),
                "profit_margin": round((float(r.profit) / float(r.revenue) * 100), 2) if r.revenue > 0 else 0
            }
            for r in results
        ]
    }


@router.get("/category-performance")
def get_category_performance(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get sales performance by menu category
    """
    
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    params = {
        "org_id": str(organization_id),
        "start_date": start_date,
        "end_date": end_date
    }
    
    outlet_filter = ""
    if outlet_id:
        outlet_filter = " AND so.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    results = db.execute(
        text(f"""
            SELECT 
                m.category,
                COUNT(DISTINCT soi.id) as items_sold,
                SUM(soi.qty) as total_qty,
                SUM(soi.total_item_amount) as revenue,
                SUM(soi.hpp_at_that_time * soi.qty) as cost,
                SUM(soi.total_item_amount - (soi.hpp_at_that_time * soi.qty)) as profit
            FROM sales_order_items soi
            JOIN sales_orders so ON so.id = soi.sales_order_id
            JOIN menus m ON m.id = soi.menu_id
            WHERE so.organization_id = :org_id
            AND so.order_datetime >= :start_date
            AND so.order_datetime <= :end_date
            {outlet_filter}
            GROUP BY m.category
            ORDER BY revenue DESC
        """),
        params
    ).fetchall()
    
    total_revenue = sum(float(r.revenue) for r in results)
    
    return {
        "period": {
            "start_date": start_date.date(),
            "end_date": end_date.date()
        },
        "categories": [
            {
                "category": r.category or "Uncategorized",
                "items_sold": r.items_sold,
                "total_qty": r.total_qty,
                "revenue": float(r.revenue),
                "cost": float(r.cost),
                "profit": float(r.profit),
                "profit_margin": round((float(r.profit) / float(r.revenue) * 100), 2) if r.revenue > 0 else 0,
                "revenue_percentage": round((float(r.revenue) / total_revenue * 100), 2) if total_revenue > 0 else 0
            }
            for r in results
        ],
        "total_revenue": total_revenue
    }


@router.get("/inventory-valuation")
def get_inventory_valuation(
    outlet_id: Optional[UUID] = Query(None, description="Filter by outlet"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current inventory valuation
    """
    
    params = {"org_id": str(organization_id)}
    outlet_filter = ""
    
    if outlet_id:
        outlet_filter = " AND s.outlet_id = :outlet_id"
        params["outlet_id"] = str(outlet_id)
    
    results = db.execute(
        text(f"""
            SELECT 
                o.name as outlet_name,
                i.name as ingredient_name,
                c.name as category_name,
                u.symbol as unit_symbol,
                s.qty_on_hand,
                s.last_cost,
                (s.qty_on_hand * s.last_cost) as total_value,
                CASE 
                    WHEN s.qty_on_hand < 10 THEN 'LOW'
                    WHEN s.qty_on_hand < 50 THEN 'MEDIUM'
                    ELSE 'GOOD'
                END as stock_status
            FROM inventory_stock s
            JOIN ingredients i ON i.id = s.ingredient_id
            JOIN units u ON u.id = s.unit_id
            JOIN outlets o ON o.id = s.outlet_id
            LEFT JOIN ingredient_categories c ON c.id = i.category_id
            WHERE s.organization_id = :org_id
            {outlet_filter}
            ORDER BY total_value DESC
        """),
        params
    ).fetchall()
    
    total_valuation = sum(float(r.total_value) for r in results if r.total_value)
    low_stock_count = sum(1 for r in results if r.stock_status == 'LOW')
    
    return {
        "total_valuation": round(total_valuation, 2),
        "total_items": len(results),
        "low_stock_count": low_stock_count,
        "items": [
            {
                "outlet_name": r.outlet_name,
                "ingredient_name": r.ingredient_name,
                "category": r.category_name,
                "qty_on_hand": float(r.qty_on_hand),
                "unit_symbol": r.unit_symbol,
                "last_cost": float(r.last_cost) if r.last_cost else 0,
                "total_value": float(r.total_value) if r.total_value else 0,
                "stock_status": r.stock_status
            }
            for r in results
        ]
    }


@router.get("/outlet-comparison")
def get_outlet_comparison(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    organization_id: UUID = Depends(get_organization_context),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Compare performance across outlets
    """
    
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    results = db.execute(
        text("""
            SELECT 
                o.id as outlet_id,
                o.name as outlet_name,
                o.type as outlet_type,
                COUNT(DISTINCT so.id) as transactions,
                SUM(so.total_amount) as revenue,
                SUM(soi.hpp_at_that_time * soi.qty) as cost,
                SUM(so.total_amount - (soi.hpp_at_that_time * soi.qty)) as profit,
                AVG(so.total_amount) as avg_transaction
            FROM outlets o
            LEFT JOIN sales_orders so ON so.outlet_id = o.id
                AND so.order_datetime >= :start_date
                AND so.order_datetime <= :end_date
            LEFT JOIN sales_order_items soi ON soi.sales_order_id = so.id
            WHERE o.organization_id = :org_id
            GROUP BY o.id, o.name, o.type
            ORDER BY revenue DESC NULLS LAST
        """),
        {
            "org_id": str(organization_id),
            "start_date": start_date,
            "end_date": end_date
        }
    ).fetchall()
    
    total_revenue = sum(float(r.revenue) if r.revenue else 0 for r in results)
    
    return {
        "period": {
            "start_date": start_date.date(),
            "end_date": end_date.date()
        },
        "outlets": [
            {
                "outlet_id": str(r.outlet_id),
                "outlet_name": r.outlet_name,
                "outlet_type": r.outlet_type,
                "transactions": r.transactions or 0,
                "revenue": float(r.revenue) if r.revenue else 0,
                "cost": float(r.cost) if r.cost else 0,
                "profit": float(r.profit) if r.profit else 0,
                "profit_margin": round((float(r.profit) / float(r.revenue) * 100), 2) if r.revenue and r.revenue > 0 else 0,
                "avg_transaction": float(r.avg_transaction) if r.avg_transaction else 0,
                "revenue_share": round((float(r.revenue) / total_revenue * 100), 2) if r.revenue and total_revenue > 0 else 0
            }
            for r in results
        ],
        "total_revenue": total_revenue
    }