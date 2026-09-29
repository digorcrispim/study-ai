from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question, UserAnswer
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
    "/material/{material_id}/adaptive/{user_id}",
    response_model=list[QuestionStudyResponse],
)
def list_adaptive_questions(
    material_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
):
    questions_statement = (
        select(Question)
        .where(Question.material_id == material_id)
        .order_by(Question.created_at.desc())
    )

    questions = db.scalars(questions_statement).all()

    if not questions:
        return []

    question_ids = [question.id for question in questions]

    answers_statement = (
        select(UserAnswer)
        .where(
            UserAnswer.user_id == user_id,
            UserAnswer.question_id.in_(question_ids),
        )
        .order_by(UserAnswer.answered_at.desc())
    )

    answers = db.scalars(answers_statement).all()

    latest_answers = {}

    for answer in answers:
        if answer.question_id not in latest_answers:
            latest_answers[answer.question_id] = answer

    wrong_questions = []
    unanswered_questions = []
    correct_questions = []

    for question in questions:
        latest_answer = latest_answers.get(question.id)

        if latest_answer is None:
            unanswered_questions.append(question)
        elif not latest_answer.is_correct:
            wrong_questions.append(question)
        else:
            correct_questions.append(question)

    wrong_questions.sort(
        key=lambda question: latest_answers[question.id].answered_at,
        reverse=True,
    )

    unanswered_questions.sort(
        key=lambda question: question.created_at,
        reverse=True,
    )

    correct_questions.sort(
        key=lambda question: latest_answers[question.id].answered_at,
        reverse=True,
    )

    return (
        wrong_questions
        + unanswered_questions
        + correct_questions
    )


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
