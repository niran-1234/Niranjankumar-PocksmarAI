import json
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import create_session_token, get_current_user, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models import RecommendationHistory, User
from app.schemas import HomeRequest, PartyRequest, JewelryRequest, LoginRequest, RegisterRequest
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api")
settings = get_settings()
gemini = GeminiService()


def save_history(db: Session, user_id: int, planner: str, budget: int, input_data: dict, result: dict):
    row = RecommendationHistory(
        user_id=user_id,
        planner_type=planner,
        budget=budget,
        input_json=json.dumps(input_data, ensure_ascii=False),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/health")
def health():
    return {"status": "ok", "gemini_configured": gemini.enabled, "model": settings.gemini_model}


@router.post("/register")
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email is already registered")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(settings.session_cookie_name, create_session_token(user.id), httponly=True, samesite="lax", max_age=settings.session_days*86400)
    return {"message": "Registration successful", "user": {"id": user.id, "name": user.name, "email": user.email}}


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    response.set_cookie(settings.session_cookie_name, create_session_token(user.id), httponly=True, samesite="lax", max_age=settings.session_days*86400)
    return {"message": "Login successful", "user": {"id": user.id, "name": user.name, "email": user.email}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.session_cookie_name)
    return {"message": "Logged out"}


@router.get("/session-info")
def session_info(user: User = Depends(get_current_user)):
    return {"logged_in": True, "user": {"id": user.id, "name": user.name, "email": user.email}}


@router.get("/session-data")
def session_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.scalar(select(RecommendationHistory).where(RecommendationHistory.user_id == user.id))
    return {"user": {"id": user.id, "name": user.name, "email": user.email}, "recommendation_count": len(user.recommendations) if user.recommendations else 0}


@router.post("/generate-home")
def generate_home(payload: HomeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    result, ai = gemini.generate("home", data)
    result["ai_powered"] = ai
    result["disclaimer"] = "Prices and availability are estimates unless verified through a live retailer/vendor integration."
    save_history(db, user.id, "home", payload.budget, data, result)
    return result


@router.post("/generate-party")
def generate_party(payload: PartyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    result, ai = gemini.generate("party", data)
    result["ai_powered"] = ai
    result["disclaimer"] = "Prices, venue availability, menus, and service availability are estimates unless verified live."
    save_history(db, user.id, "party", payload.budget, data, result)
    return result


@router.post("/generate-jewelry")
async def generate_jewelry(
    request: Request,
    budget: int = Form(...),
    occasion: str = Form(...),
    style: str = Form("Elegant"),
    outfit_description: str = Form(""),
    outfit_image: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = JewelryRequest(budget=budget, occasion=occasion, style=style, outfit_description=outfit_description)
    image_bytes = None
    mime = None
    if outfit_image and outfit_image.filename:
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if outfit_image.content_type not in allowed:
            raise HTTPException(400, "Outfit image must be JPG, PNG, or WEBP")
        image_bytes = await outfit_image.read()
        if len(image_bytes) > settings.max_image_mb * 1024 * 1024:
            raise HTTPException(413, f"Image must be {settings.max_image_mb} MB or smaller")
        mime = outfit_image.content_type

    data = payload.model_dump()
    result, ai = gemini.generate("jewelry", data, image_bytes, mime)
    result["ai_powered"] = ai
    result["disclaimer"] = "Jewelry prices and availability are estimates; verify seller details before purchasing."
    save_history(db, user.id, "jewelry", payload.budget, data, result)
    return result


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(RecommendationHistory)
        .where(RecommendationHistory.user_id == user.id)
        .order_by(RecommendationHistory.created_at.desc())
    ).all()
    return [{"id": r.id, "planner": r.planner_type, "budget": r.budget, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/history/{history_id}")
def history_detail(history_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(RecommendationHistory).where(RecommendationHistory.id == history_id, RecommendationHistory.user_id == user.id))
    if not row:
        raise HTTPException(404, "History item not found")
    return json.loads(row.result_json)


@router.delete("/history/{history_id}")
def delete_history(history_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(RecommendationHistory).where(RecommendationHistory.id == history_id, RecommendationHistory.user_id == user.id))
    if not row:
        raise HTTPException(404, "History item not found")
    db.delete(row)
    db.commit()
    return {"message": "History deleted"}
