from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question, UserAnswer
from backend.models.schemas import QuestionCreate, QuestionResponse, QuestionStudyResponse
from backend.services.topic_normalization import canonical_topic_key

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
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    topic_filter_key = canonical_topic_key(topic) if topic is not None else ""

    ranked_answers = (
        select(
            UserAnswer.question_id.label("question_id"),
            UserAnswer.is_correct.label("is_correct"),
            UserAnswer.answered_at.label("answered_at"),
            Question.topics.label("topics"),
            func.row_number()
            .over(
                partition_by=UserAnswer.question_id,
                order_by=UserAnswer.answered_at.desc(),
            )
            .label("answer_rank"),
        )
        .join(Question, UserAnswer.question_id == Question.id)
        .where(UserAnswer.user_id == user_id)
        .subquery()
    )

    latest_answers_statement = select(
        ranked_answers.c.question_id,
        ranked_answers.c.is_correct,
        ranked_answers.c.answered_at,
        ranked_answers.c.topics,
    ).where(ranked_answers.c.answer_rank == 1)
    latest_user_answers = db.execute(latest_answers_statement).all()
    latest_answers = {
        answer.question_id: answer
        for answer in latest_user_answers
    }

    topic_stats = {}

    for answer in latest_user_answers:
        topic_keys = {
            canonical_topic_key(topic)
            for topic in answer.topics or []
        }
        topic_keys.discard("")

        for topic_key in topic_keys:
            if topic_key not in topic_stats:
                topic_stats[topic_key] = {
                    "total": 0,
                    "correct": 0,
                }

            topic_stats[topic_key]["total"] += 1

            if answer.is_correct:
                topic_stats[topic_key]["correct"] += 1

    topic_accuracy = {}

    for topic_key, stats in topic_stats.items():
        total = stats["total"]
        correct = stats["correct"]

        topic_accuracy[topic_key] = (
            correct / total
            if total > 0
            else 0.5
        )

    question_accuracy_cache = {}

    def question_topic_accuracy(question):
        if question.question_id in question_accuracy_cache:
            return question_accuracy_cache[question.question_id]

        topic_keys = {
            canonical_topic_key(topic)
            for topic in question.topics or []
        }
        topic_keys.discard("")
        accuracies = [
            topic_accuracy[topic_key]
            for topic_key in topic_keys
            if topic_key in topic_accuracy
        ]

        accuracy = min(accuracies) if accuracies else 0.5
        question_accuracy_cache[question.question_id] = accuracy
        return accuracy

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

    def wrong_question_sort_key(question):
        return (
            question_topic_accuracy(question),
            difficulty_distance(question),
            -latest_answers[question.question_id].answered_at.timestamp(),
        )

    def unanswered_question_sort_key(question):
        return (
            question_topic_accuracy(question),
            difficulty_distance(question),
            -question.created_at.timestamp(),
        )

    correct_question_sort_key = wrong_question_sort_key

    wrong_questions = []
    unanswered_questions = []
    correct_questions = []
    candidate_statement = (
        select(
            Question.id.label("question_id"),
            Question.topics.label("topics"),
            Question.difficulty.label("difficulty"),
            Question.created_at.label("created_at"),
        )
        .where(Question.material_id == material_id)
        .order_by(Question.created_at.desc())
    )
    candidate_rows = db.execute(candidate_statement).all()

    for question in candidate_rows:
        if topic_filter_key and not any(
            canonical_topic_key(question_topic) == topic_filter_key
            for question_topic in question.topics or []
        ):
            continue

        latest_answer = latest_answers.get(question.question_id)

        if latest_answer is None:
            unanswered_questions.append(question)
        elif not latest_answer.is_correct:
            wrong_questions.append(question)
        else:
            correct_questions.append(question)

    wrong_questions.sort(key=wrong_question_sort_key)
    unanswered_questions.sort(key=unanswered_question_sort_key)
    correct_questions.sort(key=correct_question_sort_key)
    ordered_questions = (
        wrong_questions
        + unanswered_questions
        + correct_questions
    )
    if limit is not None:
        ordered_questions = ordered_questions[:limit]

    if not ordered_questions:
        return []

    ordered_question_ids = [
        question.question_id
        for question in ordered_questions
    ]
    response_statement = select(
        Question.id.label("id"),
        Question.material_id.label("material_id"),
        Question.question_text.label("question_text"),
        Question.options.label("options"),
        Question.topics.label("topics"),
        Question.difficulty.label("difficulty"),
        Question.explanation.label("explanation"),
    ).where(Question.id.in_(ordered_question_ids))
    response_rows = db.execute(response_statement).all()
    response_by_id = {
        row.id: {
            "id": row.id,
            "material_id": row.material_id,
            "question_text": row.question_text,
            "options": row.options,
            "topics": row.topics,
            "difficulty": row.difficulty,
            "explanation": row.explanation,
        }
        for row in response_rows
    }

    return [
        response_by_id[question_id]
        for question_id in ordered_question_ids
    ]


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
