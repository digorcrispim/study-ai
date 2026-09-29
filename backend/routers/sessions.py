from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import StudySession
from backend.models.schemas import (
    StudySessionComplete,
    StudySessionCreate,
    StudySessionResponse,
)

router = APIRouter(prefix="/sessions", tags=["Sessões"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=StudySessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    session_data: StudySessionCreate,
    db: Session = Depends(get_db),
):
    session = StudySession(
        user_id=session_data.user_id,
        material_id=session_data.material_id,
        mode=session_data.mode,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.post(
    "/{session_id}/complete",
    response_model=StudySessionResponse,
)
def complete_session(
    session_id: UUID,
    session_data: StudySessionComplete,
    db: Session = Depends(get_db),
):
    session = db.get(StudySession, session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada.",
        )

    if session_data.correct_answers > session_data.total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O número de acertos não pode ser maior que o total de questões.",
        )

    session.total_questions = session_data.total_questions
    session.correct_answers = session_data.correct_answers
    session.accuracy = (
        (session_data.correct_answers / session_data.total_questions) * 100
        if session_data.total_questions > 0
        else 0.0
    )

    from sqlalchemy import func

    session.completed_at = db.execute(
        func.now().select()
    ).scalar_one()

    db.commit()
    db.refresh(session)

    return session


@router.get(
    "/user/{user_id}",
    response_model=list[StudySessionResponse],
)
def list_user_sessions(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    from sqlalchemy import select

    statement = (
        select(StudySession)
        .where(StudySession.user_id == user_id)
        .order_by(StudySession.started_at.desc())
    )

    return db.scalars(statement).all()
