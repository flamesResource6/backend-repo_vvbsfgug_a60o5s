from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from schemas import Product, Order
from database import create_document, get_documents

app = FastAPI(title="Digital Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test")
async def test():
    items = await get_documents("product", {}, 1)
    return {"ok": True, "db_connected": True, "sample_count": len(items)}

@app.post("/products", response_model=dict)
async def create_product(product: Product):
    data = await create_document("product", product.model_dump())
    return {"product": data}

@app.get("/products", response_model=dict)
async def list_products(category: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, level: Optional[str] = None, limit: int = 50):
    filter_q = {}
    if category:
        filter_q["category"] = category
    if level:
        filter_q["level"] = level
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        filter_q["price"] = price_filter
    items = await get_documents("product", filter_q, limit)
    return {"products": items}

@app.get("/products/{slug}", response_model=dict)
async def get_product(slug: str):
    items = await get_documents("product", {"slug": slug}, 1)
    if not items:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": items[0]}

@app.post("/checkout", response_model=dict)
async def checkout(order: Order):
    # In a real app, integrate payment gateway here. For now, auto-mark paid and return a download link.
    paid = order.model_dump()
    paid["status"] = "paid"
    paid["download_url"] = paid.get("download_url") or "https://example.com/download/" + paid["product_id"]
    record = await create_document("order", paid)
    return {"order": record}
