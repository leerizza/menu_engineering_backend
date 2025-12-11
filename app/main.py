from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager


from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.api.v1 import (
    auth, 
    organizations, 
    outlets, 
    ingredients, 
    suppliers, 
    units,
    inventory, 
    purchase_orders,
    stock_requests,
    stock_transfers,
    menus,
    sales,
    analytics
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant Restaurant Management System with Menu Engineering Analytics",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_headers=["*"],
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# Health check
@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Test timezone endpoint
@app.get("/test-timezone")
def test_timezone(db: Session = Depends(get_db)):
    from sqlalchemy import text
    
    result = db.execute(text("""
        SELECT 
            NOW() as server_time,
            CURRENT_TIMESTAMP as current_timestamp,
            NOW() AT TIME ZONE 'UTC' as utc_time,
            NOW() AT TIME ZONE 'Asia/Jakarta' as jakarta_time
    """)).fetchone()
    
    timezone_setting = db.execute(text("SHOW timezone")).fetchone()
    
    return {
        "server_time": str(result[0]),
        "current_timestamp": str(result[1]),
        "utc_time": str(result[2]),
        "jakarta_time": str(result[3]),
        "timezone_setting": timezone_setting[0] if timezone_setting else "unknown"
    }


# Authentication Router
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["🔐 Authentication"]
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_PREFIX}/organizations", tags=["Organizations"])
app.include_router(outlets.router, prefix=f"{settings.API_V1_PREFIX}/outlets", tags=["Outlets"])
app.include_router(ingredients.router, prefix=f"{settings.API_V1_PREFIX}/ingredients", tags=["Ingredients"])
app.include_router(suppliers.router, prefix=f"{settings.API_V1_PREFIX}/suppliers", tags=["Suppliers"])
app.include_router(units.router, prefix=f"{settings.API_V1_PREFIX}/units", tags=["Units"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_PREFIX}/inventory", tags=["Inventory"])
app.include_router(purchase_orders.router, prefix=f"{settings.API_V1_PREFIX}/purchase-orders", tags=["Purchase Orders"])
app.include_router(stock_requests.router, prefix=f"{settings.API_V1_PREFIX}/stock-requests", tags=["Stock Requests"])
app.include_router(stock_transfers.router, prefix=f"{settings.API_V1_PREFIX}/stock-transfers", tags=["Stock Transfers"])
app.include_router(menus.router, prefix=f"{settings.API_V1_PREFIX}/menus", tags=["Menus & Recipes"])
app.include_router(sales.router, prefix=f"{settings.API_V1_PREFIX}/sales", tags=["Sales & POS"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)