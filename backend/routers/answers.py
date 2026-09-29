from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question, UserAnswer
from backend.models.schemas import (
    UserAnswerCreate,
    UserAnswerResponse,
    UserAnswerSummaryResponse,
)

router = APIRouter(prefix="/questions", tags=["Respostas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/{question_id}/answer",
    response_model=UserAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def answer_question(
    question_id: UUID,
    answer_data: UserAnswerCreate,
    db: Session = Depends(get_db),
):
    question = db.get(Question, question_id)

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questão não encontrada.",
        )

    is_correct = answer_data.selected_answer == question.correct_answer

    user_answer = UserAnswer(
        user_id=answer_data.user_id,
        question_id=question_id,
        selected_answer=answer_data.selected_answer,
        is_correct=is_correct,
    )

    db.add(user_answer)
    db.commit()
    db.refresh(user_answer)

    return user_answer



@router.get(
    "/user/{user_id}/answers",
    response_model=list[UserAnswerResponse],
)
def list_user_answers(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    statement = (
        select(UserAnswer)
        .where(UserAnswer.user_id == user_id)
        .order_by(UserAnswer.answered_at.desc())
    )

    return db.scalars(statement).all()



@router.get(
    "/user/{user_id}/summary",
    response_model=UserAnswerSummaryResponse,
)
def get_user_summary(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    statement = select(UserAnswer).where(UserAnswer.user_id == user_id)
    answers = db.scalars(statement).all()

    total_answers = len(answers)
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    incorrect_answers = total_answers - correct_answers

    accuracy = (
        (correct_answers / total_answers) * 100
        if total_answers > 0
        else 0.0
    )

    return {
        "user_id": user_id,
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "accuracy": accuracy,
    }
