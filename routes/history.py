from typing import List

from fastapi import APIRouter, HTTPException

from models.schemas import HistorySession
from services import firebase_service

router = APIRouter()


@router.get("/history/{user_id}", response_model=List[HistorySession])
async def get_history(user_id: str):
    try:
        return await firebase_service.get_user_history(user_id)
    except RuntimeError:
        return []  # Firebase not configured on this instance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
