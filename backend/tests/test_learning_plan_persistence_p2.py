"""Testes do P2: persistência do Learning Plan.

Cobre:
- geração do primeiro plano persistido;
- persistência dos itens;
- preservação de topic/action/priority;
- persistência dos snapshots de accuracy e total_answers;
- persistência de reason;
- criação do novo plano como active;
- arquivamento do plano active anterior;
- existência de apenas um active após nova geração;
- recuperação pelo GET /learning-plan/{user_id}/current;
- retorno 404 quando não existe plano ativo;
- equivalência entre o cálculo atual e os dados persistidos;
- ausência de regressão no endpoint GET atual.
"""

import unittest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models.entities import LearningPlan, LearningPlanItem, Question, UserAnswer
from backend.routers.learning_plan import get_db, router


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSessionV2:
    """FakeSession que suporta execute, scalars, add, commit, refresh.
    Simula defaults de UUID e timestamp que normalmente viriam do banco."""

    def __init__(self, question_answer_rows=()):
        self.rows = list(question_answer_rows)
        self.user_id = None
        self.statements = []
        self.added_objects = []
        self.committed = False

    def _apply_defaults(self, obj):
        """Aplica defaults que normalmente seriam preenchidos pelo banco."""
        if isinstance(obj, LearningPlan):
            if obj.id is None:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if obj.updated_at is None:
                obj.updated_at = datetime.now(timezone.utc)
        elif isinstance(obj, LearningPlanItem):
            if obj.id is None:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            # learning_plan_id já é setado pelo código

    def execute(self, statement):
        self.statements.append(statement)
        selected_columns = set(statement.selected_columns.keys())

        if selected_columns == {
            "question_id",
            "topics",
            "material_id",
            "total_answers",
            "correct_answers",
        }:
            questions = {}
            answers_by_question = {}
            for question, answer in self.rows:
                questions[question.id] = question
                if answer is not None and answer.user_id == self.user_id:
                    answers_by_question.setdefault(question.id, []).append(answer)

            result_rows = [
                (
                    question.id,
                    question.topics,
                    question.material_id,
                    len(answers_by_question.get(question.id, [])),
                    sum(
                        answer.is_correct
                        for answer in answers_by_question.get(question.id, [])
                    ),
                )
                for question in questions.values()
            ]
            return FakeResult(result_rows)
        else:
            return FakeResult([])

    def scalars(self, statement):
        self.statements.append(statement)
        query_str = str(statement)

        if "learning_plans" in query_str:
            matching = [
                obj for obj in self.added_objects
                if isinstance(obj, LearningPlan)
            ]
            # Aplicar filtros de user_id e status
            filtered = []
            for plan in matching:
                include = True
                query_lower = query_str.lower()
                if "status" in query_lower:
                    if "active" in query_lower and plan.status != "active":
                        include = False
                    if "archived" in query_lower and plan.status != "archived":
                        include = False
                if include:
                    filtered.append(plan)
            return FakeScalarResult(filtered)

        return FakeScalarResult([])

    def add(self, obj):
        self._apply_defaults(obj)
        self.added_objects.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass

    def close(self):
        pass


class P2TestBase(unittest.TestCase):
    def setUp(self):
        self.db = FakeSessionV2()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.user_id = uuid4()
        self.db.user_id = self.user_id

    def tearDown(self):
        self.client.close()

    def add_question(self, topics, material_id=None, answers=()):
        question = Question(
            id=uuid4(),
            material_id=material_id,
            question_text="Pergunta de teste",
            options={"0": "A"},
            correct_answer=0,
            topics=topics,
            difficulty="easy",
        )

        if answers:
            for is_correct in answers:
                answer = UserAnswer(
                    id=uuid4(),
                    user_id=self.user_id,
                    question_id=question.id,
                    selected_answer=0,
                    is_correct=is_correct,
                )
                self.db.rows.append((question, answer))
        else:
            self.db.rows.append((question, None))

        return question


class TestGenerateFirstPlan(P2TestBase):
    def test_first_plan_is_active(self):
        material_id = uuid4()
        self.add_question(["Racionalidade"], material_id, [True, False, True])

        response = self.client.post(f"/learning-plan/{self.user_id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["user_id"], str(self.user_id))

    def test_plan_has_items(self):
        material_id = uuid4()
        self.add_question(["Racionalidade"], material_id, [True, False, True])
        self.add_question(["Falácias"], material_id, [False, False, False])

        response = self.client.post(f"/learning-plan/{self.user_id}")

        data = response.json()
        self.assertEqual(len(data["items"]), 2)

    def test_preserves_topic_action_priority(self):
        material_id = uuid4()
        self.add_question(["Reforçar"], material_id, [False, False, False])
        self.add_question(["Aprofundar"], material_id, [True, True, True, True, False])

        # Primeiro obter o cálculo atual para comparar
        computed = self.client.get(f"/learning-plan/{self.user_id}").json()
        computed_items = {i["topic"]: i for i in computed["items"]}

        # Depois persistir
        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()
        persisted_items = {i["topic"]: i for i in persisted["items"]}

        for topic, computed_item in computed_items.items():
            self.assertIn(topic, persisted_items)
            self.assertEqual(persisted_items[topic]["action"], computed_item["action"])
            self.assertEqual(persisted_items[topic]["priority"], computed_item["priority"])

    def test_persists_accuracy_snapshot(self):
        material_id = uuid4()
        self.add_question(["Teste"], material_id, [True, False, True])

        computed = self.client.get(f"/learning-plan/{self.user_id}").json()
        computed_item = computed["items"][0]

        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()
        persisted_item = persisted["items"][0]

        self.assertEqual(
            persisted_item["accuracy_snapshot"],
            computed_item["accuracy"],
        )

    def test_persists_total_answers_snapshot(self):
        material_id = uuid4()
        self.add_question(["Teste"], material_id, [True, False, True])

        computed = self.client.get(f"/learning-plan/{self.user_id}").json()
        computed_item = computed["items"][0]

        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()
        persisted_item = persisted["items"][0]

        self.assertEqual(
            persisted_item["total_answers_snapshot"],
            computed_item["total_answers"],
        )

    def test_persists_reason(self):
        material_id = uuid4()
        self.add_question(["Teste"], material_id, [False, False, False])

        computed = self.client.get(f"/learning-plan/{self.user_id}").json()
        computed_item = computed["items"][0]

        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()
        persisted_item = persisted["items"][0]

        self.assertEqual(persisted_item["reason"], computed_item["reason"])

    def test_persists_material_id(self):
        material_id = uuid4()
        self.add_question(["Teste"], material_id, [True, False, True])

        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()
        persisted_item = persisted["items"][0]

        self.assertEqual(persisted_item["material_id"], str(material_id))


class TestArchivePreviousPlan(P2TestBase):
    def test_previous_active_is_archived(self):
        material_id = uuid4()
        self.add_question(["Tópico A"], material_id, [True, False, True])

        # Primeira geração
        response1 = self.client.post(f"/learning-plan/{self.user_id}")
        self.assertEqual(response1.status_code, 200)
        plan1_id = response1.json()["id"]

        # Segunda geração deve arquivar a primeira
        response2 = self.client.post(f"/learning-plan/{self.user_id}")
        self.assertEqual(response2.status_code, 200)
        plan2_id = response2.json()["id"]

        self.assertNotEqual(plan1_id, plan2_id)

        # Verificar que plan1 foi arquivada
        plan1 = next(
            obj for obj in self.db.added_objects
            if isinstance(obj, LearningPlan) and str(obj.id) == plan1_id
        )
        self.assertEqual(plan1.status, "archived")

        # Verificar que plan2 está active
        plan2 = next(
            obj for obj in self.db.added_objects
            if isinstance(obj, LearningPlan) and str(obj.id) == plan2_id
        )
        self.assertEqual(plan2.status, "active")

    def test_only_one_active_after_regeneration(self):
        material_id = uuid4()
        self.add_question(["Tópico"], material_id, [True, False, True])

        self.client.post(f"/learning-plan/{self.user_id}")
        self.client.post(f"/learning-plan/{self.user_id}")
        self.client.post(f"/learning-plan/{self.user_id}")

        active_plans = [
            obj for obj in self.db.added_objects
            if isinstance(obj, LearningPlan) and obj.status == "active"
        ]
        self.assertEqual(len(active_plans), 1)


class TestGetCurrentPlan(P2TestBase):
    def test_retrieves_active_plan(self):
        material_id = uuid4()
        self.add_question(["Tópico"], material_id, [True, False, True])

        # Persistir
        post_response = self.client.post(f"/learning-plan/{self.user_id}")
        plan_id = post_response.json()["id"]
        items_count = len(post_response.json()["items"])

        # Recuperar
        response = self.client.get(f"/learning-plan/{self.user_id}/current")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], plan_id)
        self.assertEqual(data["status"], "active")
        self.assertEqual(len(data["items"]), items_count)

    def test_returns_404_when_no_active_plan(self):
        material_id = uuid4()
        self.add_question(["Tópico"], material_id)

        response = self.client.get(f"/learning-plan/{self.user_id}/current")

        self.assertEqual(response.status_code, 404)
        self.assertIn("ativo", response.json()["detail"].lower())

    def test_current_does_not_recalculate(self):
        """O GET /current deve retornar os dados persistidos,
        não recalcular. Verifica comparando com o GET de cálculo."""
        material_id = uuid4()
        self.add_question(["Tópico"], material_id, [True, False, True])

        # Persistir
        self.client.post(f"/learning-plan/{self.user_id}")

        # Adicionar nova resposta (que mudaria o cálculo)
        self.add_question(["Tópico"], material_id, [False])

        # GET /current deve retornar o snapshot antigo
        current = self.client.get(f"/learning-plan/{self.user_id}/current")
        current_items = current.json()["items"]
        self.assertEqual(len(current_items), 1)
        self.assertEqual(current_items[0]["total_answers_snapshot"], 3)

        # GET /{user_id} (cálculo) deve refletir a nova realidade
        computed = self.client.get(f"/learning-plan/{self.user_id}")
        computed_items = computed.json()["items"]
        self.assertEqual(computed_items[0]["total_answers"], 4)


class TestEquivalenceWithCalculation(P2TestBase):
    def test_persisted_matches_computed(self):
        material_id = uuid4()
        self.add_question(["Reforçar"], material_id, [False, False, False])
        self.add_question(["Consolidar"], material_id, [True, True, False, False])
        self.add_question(["Aprofundar"], material_id, [True, True, True, True, False])
        self.add_question(["Explorar"], material_id, [False])

        computed = self.client.get(f"/learning-plan/{self.user_id}").json()
        persisted = self.client.post(f"/learning-plan/{self.user_id}").json()

        computed_by_topic = {i["topic"]: i for i in computed["items"]}
        persisted_by_topic = {i["topic"]: i for i in persisted["items"]}

        self.assertEqual(
            set(computed_by_topic.keys()),
            set(persisted_by_topic.keys()),
        )

        for topic in computed_by_topic:
            c = computed_by_topic[topic]
            p = persisted_by_topic[topic]
            self.assertEqual(p["action"], c["action"])
            self.assertEqual(p["priority"], c["priority"])
            self.assertEqual(p["accuracy_snapshot"], c["accuracy"])
            self.assertEqual(p["total_answers_snapshot"], c["total_answers"])
            self.assertEqual(p["reason"], c["reason"])


class TestNoRegressionOnGetEndpoint(P2TestBase):
    def test_get_endpoint_still_works(self):
        material_id = uuid4()
        self.add_question(["Racionalidade"], material_id, [True, False, True])

        response = self.client.get(f"/learning-plan/{self.user_id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], str(self.user_id))
        self.assertEqual(data["minimum_answers_for_scored_actions"], 3)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["action"], "consolidate")


if __name__ == "__main__":
    unittest.main()
