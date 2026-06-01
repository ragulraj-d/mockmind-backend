import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from middleware.auth import get_current_user
from middleware.validation import validate_answer, validate_question
from models.schemas import (
    CompleteSessionRequest,
    EvaluateAnswerRequest,
    EvaluationResult,
    InterviewSession,
    InterviewSetupRequest,
    SessionResult,
)
from services import firebase_service, groq_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/start-interview", response_model=InterviewSession)
@limiter.limit("10/minute")
async def start_interview(
    request: Request,
    body: InterviewSetupRequest,
    current_user: dict = Depends(get_current_user),
):
    # Enforce that user can only create sessions for themselves
    if body.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="user_id does not match authenticated user")

    try:
        questions = await groq_service.generate_questions(
            interview_type=body.interview_type.value,
            domain=body.domain.value,
            difficulty=body.difficulty.value,
            num_questions=body.num_questions,
        )
        session = InterviewSession(
            session_id=str(uuid.uuid4()),
            user_id=body.user_id,
            questions=questions,
            interview_type=body.interview_type.value,
            domain=body.domain.value,
            difficulty=body.difficulty.value,
            created_at=datetime.now(),
        )
        try:
            await firebase_service.save_session(session)
        except Exception as e:
            print(f"Firebase save skipped: {e}")
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-answer", response_model=EvaluationResult)
@limiter.limit("30/minute")
async def evaluate_answer(
    request: Request,
    body: EvaluateAnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="user_id does not match authenticated user")

    # Validate + sanitise before hitting Groq
    clean_answer = validate_answer(body.answer)
    clean_question = validate_question(body.question)

    try:
        return await groq_service.evaluate_answer(
            question=clean_question,
            answer=clean_answer,
            domain=body.domain,
            difficulty=body.difficulty,
            question_id=body.question_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-session", response_model=SessionResult)
@limiter.limit("5/minute")
async def complete_session(
    request: Request,
    body: CompleteSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.user_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="user_id does not match authenticated user")

    try:
        summary = await groq_service.generate_session_summary(body.evaluations)
        scores = [e.score for e in body.evaluations]
        overall = round(sum(scores) / len(scores), 1) if scores else 0.0

        result = SessionResult(
            session_id=body.session_id,
            user_id=body.user_id,
            overall_score=overall,
            evaluations=body.evaluations,
            summary=summary["summary"],
            key_strengths=summary["key_strengths"],
            key_improvements=summary["key_improvements"],
            interview_type=body.interview_type,
            domain=body.domain,
            difficulty=body.difficulty,
            completed_at=datetime.now(),
        )
        try:
            await firebase_service.save_result(result)
        except Exception as e:
            print(f"Firebase result save skipped: {e}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
