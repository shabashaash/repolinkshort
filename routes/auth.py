from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserCreate, UserResponse, Token
from services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user, db = Depends(get_db)):
    service = AuthService()
    try:
        new_user = await service.register(user.email, user.password)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(form_data = Depends()):
    service = AuthService()
    try:
        token = await service.login(form_data.username, form_data.password)
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))