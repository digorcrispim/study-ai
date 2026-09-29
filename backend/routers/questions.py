from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question
from backend.models.schemas import QuestionCreate, QuestionResponse, QuestionStudyResponse

router = APIRouter(prefix="/questions", tags=["Questões"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
):
    question = Question(
        material_id=question_data.material_id,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_answer=question_data.correct_answer,
        explanation=question_data.explanation,
        topics=question_data.topics,
        difficulty=question_data.difficulty,
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return question


@router.get("", response_model=list[QuestionResponse])
def list_questions(db: Session = Depends(get_db)):
    statement = select(Question).order_by(Question.created_at.desc())
    return db.scalars(statement).all()


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: UUID,
    db: Session = Depends(get_db),
):
    question = db.get(Question, question_id)

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questão não encontrada.",
        )

    return question



@router.get(
    "/material/{material_id}",
    response_model=list[QuestionResponse],
)
def list_questions_by_material(
    material_id: UUID,
    db: Session = Depends(get_db),
):
    statement = (
        select(Question)
        .where(Question.material_id == material_id)
        .order_by(Question.created_at.desc())
    )

    return db.scalars(statement).all()



@router.get(
    "/material/{material_id}/study",
    response_model=list[QuestionStudyResponse],
)
def list_study_questions(
    material_id: UUID,
    db: Session = Depends(get_db),
):
    statement = (
        select(Question)
        .where(Question.material_id == material_id)
        .order_by(Question.created_at.desc())
    )

    return db.scalars(statement).all()
