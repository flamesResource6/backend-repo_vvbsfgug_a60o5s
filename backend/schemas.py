from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

# Collection: product
class Product(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    slug: str = Field(..., min_length=3, max_length=140)
    description: str = Field(..., min_length=20, max_length=5000)
    price: float = Field(..., ge=0)
    category: Literal['course','prompt','video','template','bundle','other'] = 'other'
    level: Optional[Literal['beginner','intermediate','advanced']] = None
    rating: float = Field(4.8, ge=0, le=5)
    rating_count: int = 0
    cover_url: Optional[HttpUrl] = None
    contents: Optional[List[str]] = None  # table of contents / modules
    benefits: Optional[List[str]] = None
    tags: Optional[List[str]] = None

# Collection: order
class Order(BaseModel):
    product_id: str
    email: str
    amount: float
    status: Literal['pending','paid','failed'] = 'pending'
    download_url: Optional[HttpUrl] = None
