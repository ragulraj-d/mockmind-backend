from fastapi import HTTPException, status

MAX_ANSWER_LEN = 5000
MIN_ANSWER_LEN = 0  # empty answers handled gracefully (score = 0)
MAX_QUESTION_LEN = 2000


def validate_answer(answer: str) -> str:
    """Sanitise and validate a candidate answer before sending to Groq."""
    answer = answer.strip()
    if len(answer) > MAX_ANSWER_LEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Answer too long ({len(answer)} chars). Maximum is {MAX_ANSWER_LEN}.",
        )
    # Strip null bytes and other control chars that could confuse the model
    answer = "".join(ch for ch in answer if ch >= " " or ch in "\n\t")
    return answer


def validate_question(question: str) -> str:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Question is empty")
    if len(question) > MAX_QUESTION_LEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Question too long ({len(question)} chars). Maximum is {MAX_QUESTION_LEN}.",
        )
    return question
