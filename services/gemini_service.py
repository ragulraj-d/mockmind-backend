import json
import re
from typing import List

from google import genai
from google.genai import types

from models.schemas import Question, EvaluationResult, EvaluationCriteria
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"


def _generate(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    return response.text.strip()


async def generate_questions(
    interview_type: str,
    domain: str,
    difficulty: str,
    num_questions: int,
) -> List[Question]:
    prompt = f"""You are an expert interviewer. Generate exactly {num_questions} interview questions.

Interview Type: {interview_type}
Domain: {domain}
Difficulty: {difficulty}

Return ONLY a valid JSON array. No markdown, no extra text:
[
  {{
    "id": 1,
    "question": "Question text",
    "category": "Category name",
    "expected_topics": ["topic1", "topic2"]
  }}
]

Guidelines:
- Technical: algorithms, data structures, system design, coding concepts
- HR: behavioral (STAR format), leadership, conflict resolution, teamwork
- Domain-specific: deep {domain} tools, concepts, best practices, scenarios
- Beginner: definitions, basic concepts, simple scenarios
- Intermediate: applied knowledge, trade-offs, debugging, design
- Advanced: architecture decisions, optimization, edge cases, expert knowledge

Make questions diverse — avoid repetition. Number them 1 to {num_questions}."""

    text = _generate(prompt)
    json_match = re.search(r"\[.*\]", text, re.DOTALL)
    if not json_match:
        raise ValueError("Gemini did not return a valid JSON array for questions")

    questions_data = json.loads(json_match.group())
    return [Question(**q) for q in questions_data[:num_questions]]


async def evaluate_answer(
    question: str,
    answer: str,
    domain: str,
    difficulty: str,
    question_id: int,
) -> EvaluationResult:
    if not answer.strip():
        return EvaluationResult(
            question_id=question_id,
            question=question,
            answer=answer,
            score=0.0,
            criteria=EvaluationCriteria(accuracy=0, clarity=0, depth=0, confidence=0),
            feedback="No answer was provided for this question.",
            strengths=[],
            improvements=["Attempt every question — even a partial answer shows effort."],
            model_answer_hint="Review the fundamentals of this topic.",
        )

    prompt = f"""You are an expert interviewer evaluating a candidate's answer.

Domain: {domain}
Difficulty: {difficulty}
Question: {question}
Candidate Answer: {answer}

Score each criterion 0–10. Return ONLY valid JSON, no markdown:
{{
  "score": <weighted overall 0–10, 2 decimal places>,
  "criteria": {{
    "accuracy": <0–10>,
    "clarity": <0–10>,
    "depth": <0–10>,
    "confidence": <0–10>
  }},
  "feedback": "<2–3 constructive sentences>",
  "strengths": ["<specific strength 1>", "<specific strength 2>"],
  "improvements": ["<specific improvement 1>", "<specific improvement 2>"],
  "model_answer_hint": "<one sentence hint on what a great answer covers>"
}}

Scoring guidance (adjust for {difficulty} level):
- accuracy: Is the information correct and up-to-date?
- clarity: Is it well-structured and easy to follow?
- depth: Does it show genuine understanding beyond surface level?
- confidence: Does the language show conviction and expertise?
- overall score: weighted average (accuracy 35%, depth 30%, clarity 20%, confidence 15%)

Be encouraging but honest. Tailor strictness to the {difficulty} level."""

    text = _generate(prompt)
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError("Gemini did not return valid JSON for evaluation")

    eval_data = json.loads(json_match.group())
    return EvaluationResult(
        question_id=question_id,
        question=question,
        answer=answer,
        score=round(float(eval_data["score"]), 1),
        criteria=EvaluationCriteria(**eval_data["criteria"]),
        feedback=eval_data["feedback"],
        strengths=eval_data.get("strengths", []),
        improvements=eval_data.get("improvements", []),
        model_answer_hint=eval_data.get("model_answer_hint"),
    )


async def generate_session_summary(evaluations: List[EvaluationResult]) -> dict:
    scores = [e.score for e in evaluations]
    overall = sum(scores) / len(scores) if scores else 0
    all_strengths = [s for e in evaluations for s in e.strengths][:8]
    all_improvements = [i for e in evaluations for i in e.improvements][:8]

    prompt = f"""Interview session analysis:

Overall Score: {overall:.1f}/10
Per-question Scores: {[round(s, 1) for s in scores]}
Collected Strengths: {all_strengths}
Collected Improvements: {all_improvements}

Write a 2-3 sentence motivational summary and pick top 3 strengths and top 3 improvements.
Return ONLY valid JSON:
{{
  "summary": "<motivational 2–3 sentence summary>",
  "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "key_improvements": ["<area 1>", "<area 2>", "<area 3>"]
}}"""

    try:
        text = _generate(prompt)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    return {
        "summary": f"You scored {overall:.1f}/10 overall. Great effort — keep practicing!",
        "key_strengths": all_strengths[:3] if all_strengths else ["Completed the interview"],
        "key_improvements": all_improvements[:3] if all_improvements else ["Continue practicing"],
    }
