from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import LearningPlan, LearningPlanItem
from backend.models.schemas import (
    LearningPlanResponse,
    PersistedLearningPlanResponse,
)
from backend.services.learning_plan_service import compute_learning_plan

router = APIRouter(prefix="/learning-plan", tags=["Plano de Aprendizagem"])


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
    """Calcula e retorna o Plano de Aprendizagem sem persistir."""
    return compute_learning_plan(user_id, db)


@router.post("/{user_id}", response_model=PersistedLearningPlanResponse)
def generate_and_persist_learning_plan(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Calcula e persiste um novo snapshot do Plano de Aprendizagem.

    Fluxo:
    1. Calcula o plano usando a mesma lógica do GET atual;
    2. Arquiva o plano active existente (se houver);
    3. Cria um novo LearningPlan com status="active";
    4. Cria um LearningPlanItem para cada item calculado;
    5. Persiste tudo em uma única transação;
    6. Retorna o plano recém-persistido.
    """
    computed = compute_learning_plan(user_id, db)

    # Arquivar plano active existente
    existing_active = db.scalars(
        select(LearningPlan).where(
            LearningPlan.user_id == user_id,
            LearningPlan.status == "active",
        )
    ).all()

    for plan in existing_active:
        plan.status = "archived"

    # Criar novo plano
    new_plan = LearningPlan(
        user_id=user_id,
        status="active",
    )
    db.add(new_plan)

    # Criar itens
    for item in computed["items"]:
        material_ids = item.get("material_ids", [])
        # Se houver múltiplos materiais, usar o primeiro (o mesmo critério
        # já usado pelo endpoint atual quando retorna a lista para o frontend).
        # Se houver apenas um, usar esse. Se nenhum, None.
        material_id = material_ids[0] if material_ids else None

        plan_item = LearningPlanItem(
            learning_plan_id=new_plan.id,
            topic=item["topic"],
            material_id=material_id,
            action=item["action"],
            priority=item["priority"],
            status="pending",
            accuracy_snapshot=item["accuracy"],
            total_answers_snapshot=item["total_answers"],
            reason=item["reason"],
        )
        # Associar o item ao plano pela relação, não apenas pela FK.
        # Isso garante que new_plan.items esteja populado em memória para
        # a serialização da resposta, sem depender de um reload lazy da
        # relação após o refresh.
        new_plan.items.append(plan_item)
        db.add(plan_item)

    db.commit()
    db.refresh(new_plan)

    return new_plan


@router.get("/{user_id}/current", response_model=PersistedLearningPlanResponse)
def get_current_learning_plan(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Recupera o plano ativo persistido do usuário.

    Não recalcula o plano. Caso não exista plano ativo persistido,
    retorna HTTP 404.
    """
    plan = db.scalars(
        select(LearningPlan).where(
            LearningPlan.user_id == user_id,
            LearningPlan.status == "active",
        )
    ).first()

    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum plano de aprendizagem ativo encontrado para este usuário.",
        )

    return plan
