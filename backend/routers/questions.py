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
    topic: str | None = None,
    db: Session = Depends(get_db),
):
    questions_statement = (
        select(Question)
        .where(Question.material_id == material_id)
        .order_by(Question.created_at.desc())
    )

    questions = db.scalars(questions_statement).all()

    if topic is not None:
        normalized_topic = topic.strip()
        if normalized_topic:
            questions = [
                question
                for question in questions
                if normalized_topic in (question.topics or [])
            ]

    if not questions:
        return []

    question_ids = [question.id for question in questions]

    material_answers_statement = (
        select(UserAnswer)
        .where(
            UserAnswer.user_id == user_id,
            UserAnswer.question_id.in_(question_ids),
        )
        .order_by(UserAnswer.answered_at.desc())
    )

    material_answers = db.scalars(material_answers_statement).all()

    latest_answers = {}

    for answer in material_answers:
        if answer.question_id not in latest_answers:
            latest_answers[answer.question_id] = answer

    all_answers_statement = (
        select(UserAnswer, Question)
        .join(Question, UserAnswer.question_id == Question.id)
        .where(UserAnswer.user_id == user_id)
        .order_by(UserAnswer.answered_at.desc())
    )

    all_answer_rows = db.execute(all_answers_statement).all()

    latest_user_answers = {}

    for answer, question in all_answer_rows:
        if answer.question_id not in latest_user_answers:
            latest_user_answers[answer.question_id] = (answer, question)

    topic_stats = {}

    for answer, question in latest_user_answers.values():
        for topic in set(question.topics or []):
            if topic not in topic_stats:
                topic_stats[topic] = {
                    "total": 0,
                    "correct": 0,
                }

            topic_stats[topic]["total"] += 1

            if answer.is_correct:
                topic_stats[topic]["correct"] += 1

    topic_accuracy = {}

    for topic, stats in topic_stats.items():
        total = stats["total"]
        correct = stats["correct"]

        topic_accuracy[topic] = (
            correct / total
            if total > 0
            else 0.5
        )

    def question_topic_accuracy(question):
        accuracies = [
            topic_accuracy[topic]
            for topic in set(question.topics or [])
            if topic in topic_accuracy
        ]

        if not accuracies:
            return 0.5

        return min(accuracies)

    difficulty_rank = {
        "easy": 0,
        "medium": 1,
        "hard": 2,
    }

    def target_difficulty(accuracy):
        if accuracy < 0.5:
            return 0
        if accuracy < 0.8:
            return 1
        return 2

    def difficulty_distance(question):
        current_rank = difficulty_rank.get(question.difficulty, 1)
        target_rank = target_difficulty(question_topic_accuracy(question))
        return abs(current_rank - target_rank)

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
        key=lambda question: (
            question_topic_accuracy(question),
            difficulty_distance(question),
            -latest_answers[question.id].answered_at.timestamp(),
        )
    )

    unanswered_questions.sort(
        key=lambda question: (
            question_topic_accuracy(question),
            difficulty_distance(question),
            -question.created_at.timestamp(),
        )
    )

    correct_questions.sort(
        key=lambda question: (
            question_topic_accuracy(question),
            difficulty_distance(question),
            -latest_answers[question.id].answered_at.timestamp(),
        )
    )

    return (
        wrong_questions
        + unanswered_questions
        + correct_questions
    )


@router.get(
    "/material/{material_id}/review/{user_id}",
    response_model=list[QuestionStudyResponse],
)
def list_review_questions(
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
        .order_by(UserAnswer.question_id, UserAnswer.answered_at.desc())
    )

    answers = db.scalars(answers_statement).all()

    answers_by_question = {}

    for answer in answers:
        answers_by_question.setdefault(answer.question_id, []).append(answer)

    from datetime import datetime, timedelta, timezone

    intervals = [1, 3, 7, 14, 30]

    due_questions = []

    for question in questions:
        question_answers = answers_by_question.get(question.id, [])

        if not question_answers:
            continue

        latest_answer = question_answers[0]

        if not latest_answer.is_correct:
            next_review_at = latest_answer.answered_at
        else:
            correct_streak = 0

            for answer in question_answers:
                if not answer.is_correct:
                    break
                correct_streak += 1

            interval_days = intervals[min(correct_streak - 1, len(intervals) - 1)]
            next_review_at = latest_answer.answered_at + timedelta(
                days=interval_days
            )

        now = datetime.now(timezone.utc)

        if next_review_at <= now:
            due_questions.append(
                (
                    next_review_at,
                    question,
                )
            )

    due_questions.sort(key=lambda item: item[0])

    return [question for _, question in due_questions]


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
