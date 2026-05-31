import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

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


@router.post("/start-interview", response_model=InterviewSession)
async def start_interview(request: InterviewSetupRequest):
    try:
        questions = await groq_service.generate_questions(
            interview_type=request.interview_type.value,
            domain=request.domain.value,
            difficulty=request.difficulty.value,
            num_questions=request.num_questions,
        )

        session = InterviewSession(
            session_id=str(uuid.uuid4()),
            user_id=request.user_id,
            questions=questions,
            interview_type=request.interview_type.value,
            domain=request.domain.value,
            difficulty=request.difficulty.value,
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
async def evaluate_answer(request: EvaluateAnswerRequest):
    try:
        return await groq_service.evaluate_answer(
            question=request.question,
            answer=request.answer,
            domain=request.domain,
            difficulty=request.difficulty,
            question_id=request.question_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-session", response_model=SessionResult)
async def complete_session(request: CompleteSessionRequest):
    try:
        summary = await groq_service.generate_session_summary(request.evaluations)

        scores = [e.score for e in request.evaluations]
        overall = round(sum(scores) / len(scores), 1) if scores else 0.0

        result = SessionResult(
            session_id=request.session_id,
            user_id=request.user_id,
            overall_score=overall,
            evaluations=request.evaluations,
            summary=summary["summary"],
            key_strengths=summary["key_strengths"],
            key_improvements=summary["key_improvements"],
            interview_type=request.interview_type,
            domain=request.domain,
            difficulty=request.difficulty,
            completed_at=datetime.now(),
        )

        try:
            await firebase_service.save_result(result)
        except Exception as e:
            print(f"Firebase result save skipped: {e}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
