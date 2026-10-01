from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Question, UserAnswer
from backend.models.schemas import LearningPlanResponse
from backend.services.topic_normalization import canonical_topic_key

router = APIRouter(prefix="/learning-plan", tags=["Plano de Aprendizagem"])

MINIMUM_ANSWERS_FOR_SCORED_ACTIONS = 3
ACTION_ORDER = {
    "reinforce": 0,
    "consolidate": 1,
    "deepen": 2,
    "explore": 3,
}
TOPIC_DISPLAY_LABELS = {
    "custo-benefício": "Custo-benefício",
    "falácias": "Falácias",
    "racionalidade": "Racionalidade",
    "custos irrecuperáveis": "Custos irrecuperáveis",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{user_id}", response_model=LearningPlanResponse)
def get_learning_plan(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    statement = (
        select(
            Question.id.label("question_id"),
            Question.topics.label("topics"),
            Question.material_id.label("material_id"),
            func.count(UserAnswer.id).label("total_answers"),
            func.coalesce(
                func.sum(
                    case(
                        (UserAnswer.is_correct, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("correct_answers"),
        )
        .outerjoin(
            UserAnswer,
            and_(
                UserAnswer.question_id == Question.id,
                UserAnswer.user_id == user_id,
            ),
        )
        .group_by(Question.id, Question.topics, Question.material_id)
    )
    rows = db.execute(statement).all()

    topic_stats = {}

    for _, question_topics, material_id, total_answers, correct_answers in rows:
        topic_labels_by_key = {}
        for original_topic in question_topics or []:
            topic_key = canonical_topic_key(original_topic)
            if not topic_key:
                continue
            topic_labels_by_key.setdefault(topic_key, set()).add(
                original_topic.strip()
            )

        for topic_key, original_labels in topic_labels_by_key.items():
            stats = topic_stats.setdefault(
                topic_key,
                {
                    "total_answers": 0,
                    "correct_answers": 0,
                    "material_ids": set(),
                    "original_labels": set(),
                },
            )
            stats["original_labels"].update(original_labels)
            stats["total_answers"] += total_answers
            stats["correct_answers"] += correct_answers

            if material_id is not None:
                stats["material_ids"].add(material_id)

    ordered_items = []

    for topic_key, stats in topic_stats.items():
        topic_label = TOPIC_DISPLAY_LABELS.get(
            topic_key,
            min(stats["original_labels"]),
        )
        material_ids = sorted(stats["material_ids"], key=str)
        if not material_ids:
            continue

        total_answers = stats["total_answers"]
        correct_answers = stats["correct_answers"]
        incorrect_answers = total_answers - correct_answers
        has_sufficient_data = (
            total_answers >= MINIMUM_ANSWERS_FOR_SCORED_ACTIONS
        )

        if not has_sufficient_data:
            action = "explore"
            accuracy = None
            sort_key = (ACTION_ORDER[action], total_answers, topic_key)
            reason = (
                f"Amostra insuficiente: {total_answers} resposta(s); "
                f"são necessárias pelo menos "
                f"{MINIMUM_ANSWERS_FOR_SCORED_ACTIONS} para classificar "
                "o desempenho."
            )
        else:
            raw_accuracy = correct_answers / total_answers * 100
            accuracy = round(raw_accuracy, 2)

            if raw_accuracy < 50:
                action = "reinforce"
                reason = (
                    f"Precisão de {accuracy:.2f}% abaixo de 50% "
                    f"({correct_answers}/{total_answers} acertos)."
                )
            elif raw_accuracy < 80:
                action = "consolidate"
                reason = (
                    f"Precisão de {accuracy:.2f}% entre 50% e menos de 80% "
                    f"({correct_answers}/{total_answers} acertos)."
                )
            else:
                action = "deepen"
                reason = (
                    f"Precisão de {accuracy:.2f}% igual ou acima de 80% "
                    f"({correct_answers}/{total_answers} acertos)."
                )

            sort_key = (ACTION_ORDER[action], raw_accuracy, topic_key)

        item = {
            "topic": topic_label,
            "action": action,
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "accuracy": accuracy,
            "has_sufficient_data": has_sufficient_data,
            "material_ids": material_ids,
            "requires_material_choice": len(material_ids) > 1,
            "reason": reason,
        }
        ordered_items.append((sort_key, item))

    ordered_items.sort(key=lambda entry: entry[0])

    items = [
        {**item, "priority": index}
        for index, (_, item) in enumerate(ordered_items, start=1)
    ]

    return {
        "user_id": user_id,
        "minimum_answers_for_scored_actions": (
            MINIMUM_ANSWERS_FOR_SCORED_ACTIONS
        ),
        "items": items,
    }