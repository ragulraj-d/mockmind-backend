from datetime import datetime
from typing import List, Optional

try:
    from firebase_admin import firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from models.schemas import InterviewSession, SessionResult, HistorySession


def _get_db():
    if not FIREBASE_AVAILABLE:
        raise RuntimeError("Firebase is not initialized")
    return firestore.client()


async def save_session(session: InterviewSession) -> None:
    db = _get_db()
    data = session.model_dump()
    data["created_at"] = firestore.SERVER_TIMESTAMP
    db.collection("sessions").document(session.session_id).set(data)


async def save_result(result: SessionResult) -> None:
    db = _get_db()
    data = result.model_dump()
    data["completed_at"] = firestore.SERVER_TIMESTAMP

    db.collection("results").document(result.session_id).set(data)
    db.collection("sessions").document(result.session_id).update(
        {
            "completed": True,
            "overall_score": result.overall_score,
            "completed_at": firestore.SERVER_TIMESTAMP,
        }
    )


async def get_user_history(user_id: str) -> List[HistorySession]:
    db = _get_db()
    query = (
        db.collection("sessions")
        .where("user_id", "==", user_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )

    history: List[HistorySession] = []
    for doc in query.stream():
        d = doc.to_dict()
        created = d.get("created_at")
        if isinstance(created, datetime):
            created_at = created
        else:
            created_at = datetime.now()

        completed = d.get("completed_at")
        completed_at: Optional[datetime] = completed if isinstance(completed, datetime) else None

        history.append(
            HistorySession(
                session_id=d.get("session_id", doc.id),
                interview_type=d.get("interview_type", ""),
                domain=d.get("domain", ""),
                difficulty=d.get("difficulty", ""),
                overall_score=float(d.get("overall_score", 0.0)),
                num_questions=len(d.get("questions", [])),
                created_at=created_at,
                completed_at=completed_at,
            )
        )
    return history
