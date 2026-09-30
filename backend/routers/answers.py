from backend.models.entities import Material, Question, UserAnswer
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question, UserAnswer
from backend.models.schemas import (
    UserAnswerCreate,
    UserAnswerResponse,
    UserAnswerSummaryResponse,
    UserTopicPerformanceResponse,
)
from backend.services.ai_question_service import (
    generate_adaptive_questions,
    save_generated_questions,
)
router = APIRouter(prefix="/questions", tags=["Respostas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def prepare_adaptive_questions(
    question: Question,
    user_id: UUID,
    is_correct: bool,
    db: Session,
):
    """
    Prepara questões adaptativas para o próximo estudo.

    Estratégia:
    - erro -> reforço, reduzindo a dificuldade;
    - acerto -> aprofundamento, aumentando a dificuldade;
    - primeiro reutiliza questões existentes;
    - só gera novas questões quando necessário.
    """

    # 1. Precisamos de um tópico para orientar a adaptação.
    topics = question.topics or []

    if not topics:
        return []

    topic = topics[0].strip()

    # 2. Define a nova dificuldade.
    difficulty_levels = ["easy", "medium", "hard"]
    current_index = difficulty_levels.index(question.difficulty)

    if is_correct:
        # Acertou -> aumentar a dificuldade.
        target_index = min(current_index + 1, 2)
        learning_goal = "deepen"
    else:
        # Errou -> reduzir a dificuldade para reforçar.
        target_index = max(current_index - 1, 0)
        learning_goal = "reinforce"

    target_difficulty = difficulty_levels[target_index]

    # 3. Procurar questões existentes do mesmo material,
    #    tópico e dificuldade que o usuário ainda não respondeu.
    answered_question_exists = exists().where(
    UserAnswer.user_id == user_id,
    UserAnswer.question_id == Question.id,
)

    statement = (
        select(Question)
        .where(
            Question.material_id == question.material_id,
            Question.difficulty == target_difficulty,
            Question.topics.any(topic),
            ~answered_question_exists,
        )
        .limit(3)
    )

    existing_questions = db.scalars(statement).all()


    # 4. Se já temos 3 questões disponíveis, não precisamos
    #    chamar a IA.
    if len(existing_questions) >= 3:
        return existing_questions

    # 5. Precisamos de novas questões.
    material = db.get(Material, question.material_id)

    if material is None:
        return existing_questions

    missing_questions = 3 - len(existing_questions)

    generated_questions = generate_adaptive_questions(
        material_title=material.title,
        raw_text=material.raw_text,
        topic=topic,
        difficulty=target_difficulty,
        learning_goal=learning_goal,
        number_of_questions=missing_questions,
    )

    new_questions = save_generated_questions(
        material_id=question.material_id,
        generated_questions=generated_questions,
        db=db,
    )

    return existing_questions + new_questions

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

# Prepara as próximas questões de forma adaptativa.
# A resposta já foi salva, então um problema na geração
# não impede o registro da resposta do estudante.
    try:
        adaptive_questions = prepare_adaptive_questions(
            question=question,
            user_id=answer_data.user_id,
            is_correct=is_correct,
            db=db,
        )
    except Exception as exc:
        print(f"Erro ao preparar questões adaptativas: {exc}")
        adaptive_questions = []

    return {
        "id": user_answer.id,
        "user_id": user_answer.user_id,
        "question_id": user_answer.question_id,
        "selected_answer": user_answer.selected_answer,
        "is_correct": user_answer.is_correct,
        "answered_at": user_answer.answered_at,
        "adaptive_questions": adaptive_questions,
    }


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
    "/user/{user_id}/topics",
    response_model=UserTopicPerformanceResponse,
)
def get_user_topic_performance(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    statement = (
        select(UserAnswer, Question)
        .join(Question, UserAnswer.question_id == Question.id)
        .where(UserAnswer.user_id == user_id)
    )

    rows = db.execute(statement).all()

    topic_stats = {}

    for answer, question in rows:
        for topic in set(question.topics or []):
            if topic not in topic_stats:
                topic_stats[topic] = {
                    "total_answers": 0,
                    "correct_answers": 0,
                }

            topic_stats[topic]["total_answers"] += 1

            if answer.is_correct:
                topic_stats[topic]["correct_answers"] += 1

    topics = []

    for topic, stats in sorted(topic_stats.items()):
        total_answers = stats["total_answers"]
        correct_answers = stats["correct_answers"]
        incorrect_answers = total_answers - correct_answers
        accuracy = (
            (correct_answers / total_answers) * 100
            if total_answers > 0
            else 0.0
        )

        topics.append(
            {
                "topic": topic,
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers,
                "accuracy": accuracy,
            }
        )

    return {
        "user_id": user_id,
        "topics": topics,
    }


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
