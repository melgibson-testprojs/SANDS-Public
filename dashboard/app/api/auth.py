from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uuid
import os

from dashboard.app.services.auth_service import auth_service, UserRole

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="dashboard/app/templates")

class LoginRequest(BaseModel):
    username: str
    password: str

async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in auth_service.sessions:
        return None
    return auth_service.sessions[token]

async def get_current_role(request: Request):
    username = await get_current_user(request)
    if not username:
        return None
    return auth_service.users[username]["role"]

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/api/auth/login")
async def login(response: Response, req: LoginRequest):
    role = auth_service.authenticate(req.username, req.password)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = str(uuid.uuid4())
    auth_service.sessions[token] = req.username
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax"
    )
    return {"status": "ok", "role": role}

@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return RedirectResponse(url="/login")

# Dependency to protect routes
def login_required(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user
