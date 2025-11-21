import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
