from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class InterviewType(str, Enum):
    TECHNICAL = "Technical"
    HR = "HR"
    DOMAIN = "Domain-specific"


class Domain(str, Enum):
    CYBERSECURITY = "Cybersecurity"
    SOFTWARE_DEV = "Software Development"
    DATA_SCIENCE = "Data Science"
    MACHINE_LEARNING = "Machine Learning"
    DEVOPS = "DevOps"
    CLOUD = "Cloud Computing"
    WEB_DEV = "Web Development"
    MOBILE_DEV = "Mobile Development"
    DATABASE = "Database Administration"
    NETWORKING = "Networking"


class Difficulty(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class InterviewSetupRequest(BaseModel):
    user_id: str
    interview_type: InterviewType
    domain: Domain
    difficulty: Difficulty
    num_questions: int = 10


class Question(BaseModel):
    id: int
    question: str
    category: Optional[str] = None
    expected_topics: Optional[List[str]] = None


class InterviewSession(BaseModel):
    session_id: str
    user_id: str
    questions: List[Question]
    interview_type: str
    domain: str
    difficulty: str
    created_at: datetime


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    user_id: str
    question_id: int
    question: str
    answer: str
    domain: str
    difficulty: str


class EvaluationCriteria(BaseModel):
    accuracy: float
    clarity: float
    depth: float
    confidence: float


class EvaluationResult(BaseModel):
    question_id: int
    question: str
    answer: str
    score: float
    criteria: EvaluationCriteria
    feedback: str
    strengths: List[str]
    improvements: List[str]
    model_answer_hint: Optional[str] = None


class CompleteSessionRequest(BaseModel):
    session_id: str
    user_id: str
    interview_type: str
    domain: str
    difficulty: str
    evaluations: List[EvaluationResult]


class SessionResult(BaseModel):
    session_id: str
    user_id: str
    overall_score: float
    evaluations: List[EvaluationResult]
    summary: str
    key_strengths: List[str]
    key_improvements: List[str]
    interview_type: str
    domain: str
    difficulty: str
    completed_at: datetime


class HistorySession(BaseModel):
    session_id: str
    interview_type: str
    domain: str
    difficulty: str
    overall_score: float
    num_questions: int
    created_at: datetime
    completed_at: Optional[datetime] = None
