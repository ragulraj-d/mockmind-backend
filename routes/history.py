from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from middleware.auth import get_current_user
from models.schemas import HistorySession
from services import firebase_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/history/{user_id}", response_model=List[HistorySession])
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Cannot access another user's history")
    try:
        return await firebase_service.get_user_history(user_id)
    except RuntimeError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
