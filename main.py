import os
import hmac
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: str | None = None


class CreateUPIOrderRequest(BaseModel):
    amount_inr: int = Field(..., ge=1, description="Amount in INR paise (e.g., 49900 for ₹499.00)")
    receipt: str | None = Field(None, description="Optional receipt identifier")
    notes: dict | None = Field(default_factory=dict)


class VerifyRazorpaySignatureRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.post("/subscribe")
def subscribe(payload: SubscribeRequest):
    """
    Subscribe an email to Beehiiv using backend-side API key.

    Env vars required:
    - BEEHIIV_API_KEY
    - BEEHIIV_PUBLICATION_ID
    """
    api_key = os.getenv("BEEHIIV_API_KEY")
    publication_id = os.getenv("BEEHIIV_PUBLICATION_ID")

    if not api_key or not publication_id:
        raise HTTPException(status_code=500, detail="Beehiiv not configured on server")

    url = f"https://api.beehiiv.com/v2/publications/{publication_id}/subscriptions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "email": payload.email,
        "utm_source": payload.source or "website",
        "send_welcome_email": True
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            return {"success": True}
        # Forward meaningful error from Beehiiv
        try:
            err = r.json()
        except Exception:
            err = {"message": r.text}
        raise HTTPException(status_code=r.status_code, detail=err)
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Beehiiv timeout")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Beehiiv error: {str(e)}")


# ------------------------------
# Payments: Razorpay UPI Checkout
# ------------------------------
@app.post("/payments/upi/create-order")
def create_upi_order(payload: CreateUPIOrderRequest):
    """
    Create a Razorpay order for UPI checkout.

    Required env vars:
    - RAZORPAY_KEY_ID
    - RAZORPAY_KEY_SECRET

    Amount is in paise (e.g., 49900 = ₹499.00)
    """
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=500, detail="Razorpay not configured on server")

    url = "https://api.razorpay.com/v1/orders"
    auth = (key_id, key_secret)
    data = {
        "amount": payload.amount_inr,  # in paise
        "currency": "INR",
        "receipt": payload.receipt or "rcpt_" + str(payload.amount_inr),
        "payment_capture": 1,
        "notes": payload.notes or {},
    }

    try:
        r = requests.post(url, auth=auth, json=data, timeout=10)
        r.raise_for_status()
        order = r.json()
        return {
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "key_id": key_id,
        }
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Razorpay timeout")
    except requests.HTTPError:
        try:
            err = r.json()
        except Exception:
            err = {"message": r.text}
        raise HTTPException(status_code=r.status_code, detail=err)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Razorpay error: {str(e)}")


@app.post("/payments/razorpay/verify-signature")
def verify_razorpay_signature(payload: VerifyRazorpaySignatureRequest):
    """Verify Razorpay checkout signature after payment success."""
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_secret:
        raise HTTPException(status_code=500, detail="Razorpay not configured on server")

    generated = hmac.new(
        key_secret.encode("utf-8"),
        f"{payload.order_id}|{payload.payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if hmac.compare_digest(generated, payload.signature):
        return {"valid": True}
    raise HTTPException(status_code=400, detail={"valid": False})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
