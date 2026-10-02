"""Testes do P4: atualização de status dos itens do Learning Plan.

Cobre o endpoint PATCH /learning-plan/items/{item_id}:
- atualização bem-sucedida de "pending" para "in_progress";
- atualização de "in_progress" para "completed" com preenchimento de
  completed_at (timestamp válido);
- item inexistente retorna 404;
- status inválido retorna 422 (validação do Pydantic via pattern).

Os testes usam uma sessão fake em memória (sem banco real), no mesmo
estilo dos testes P2.
"""

import unittest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models.entities import LearningPlanItem
from backend.routers.learning_plan import get_db, router


class FakeSessionP4:
    """Sessão fake que suporta get, commit e refresh para o PATCH.

    Mantém os itens em um dicionário indexado por id, permitindo que
    db.get(LearningPlanItem, item_id) devolva o objeto correto ou None.
    """

    def __init__(self):
        self.items_by_id = {}
        self.committed = False

    def seed_item(self, item):
        self.items_by_id[item.id] = item

    def get(self, model, pk):
        if model is LearningPlanItem:
            return self.items_by_id.get(pk)
        return None

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass

    def close(self):
        pass


class P4TestBase(unittest.TestCase):
    def setUp(self):
        self.db = FakeSessionP4()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def make_item(self, status="pending"):
        item = LearningPlanItem(
            id=uuid4(),
            learning_plan_id=uuid4(),
            topic="Racionalidade",
            material_id=uuid4(),
            action="reinforce",
            priority=1,
            status=status,
            accuracy_snapshot=33.33,
            total_answers_snapshot=3,
            reason="Precisão abaixo de 50%.",
            created_at=datetime(2026, 1, 1),
            completed_at=None,
        )
        self.db.seed_item(item)
        return item


class TestUpdateStatus(P4TestBase):
    def test_pending_to_in_progress(self):
        item = self.make_item(status="pending")

        response = self.client.patch(
            f"/learning-plan/items/{item.id}",
            json={"status": "in_progress"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(item.id))
        self.assertEqual(data["status"], "in_progress")
        self.assertIsNone(data["completed_at"])
        self.assertTrue(self.db.committed)

    def test_in_progress_to_completed_sets_completed_at(self):
        item = self.make_item(status="in_progress")

        response = self.client.patch(
            f"/learning-plan/items/{item.id}",
            json={"status": "completed"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertIsNotNone(data["completed_at"])

        # completed_at deve ser um timestamp ISO-8601 válido. O sufixo "Z"
        # (UTC) é normalizado para "+00:00" porque datetime.fromisoformat
        # no Python 3.10 não aceita o "Z" diretamente.
        parsed = datetime.fromisoformat(
            data["completed_at"].replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)

        # E deve ter sido efetivamente setado no objeto em memória,
        # com timezone UTC.
        self.assertIsNotNone(item.completed_at)
        self.assertEqual(item.completed_at.tzinfo, timezone.utc)

    def test_item_not_found_returns_404(self):
        missing_id = uuid4()

        response = self.client.patch(
            f"/learning-plan/items/{missing_id}",
            json={"status": "completed"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item não encontrado")

    def test_invalid_status_returns_422(self):
        item = self.make_item(status="pending")

        response = self.client.patch(
            f"/learning-plan/items/{item.id}",
            json={"status": "done"},
        )

        self.assertEqual(response.status_code, 422)
        # O status do item não deve ter mudado.
        self.assertEqual(item.status, "pending")


if __name__ == "__main__":
    unittest.main()
