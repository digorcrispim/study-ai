import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from backend.services.ai_question_service import save_generated_questions
from backend.services.ai_schemas import GeneratedQuestion, GeneratedQuestionSet


class TestGeneratedQuestionPersistence(unittest.TestCase):
    def setUp(self):
        self.material_id = uuid4()
        self.raw_questions = [
            GeneratedQuestion(
                question_text="Pergunta 1: O que é Python?",
                option_0="Uma cobra",
                option_1="Uma linguagem",
                option_2="Um framework",
                option_3="Um banco de dados",
                correct_answer=1,
                explanation="Python é uma linguagem de programação.",
                topics=["Python", "Introdução"],
                difficulty="easy",
            ),
            GeneratedQuestion(
                question_text="Pergunta 2: O que é FastAPI?",
                option_0="Um banco",
                option_1="Uma biblioteca de gráficos",
                option_2="Um framework web moderno",
                option_3="Um sistema operacional",
                correct_answer=2,
                explanation="FastAPI é um framework web assíncrono para Python.",
                topics=["FastAPI", "Web"],
                difficulty="medium",
            ),
            GeneratedQuestion(
                question_text="Pergunta 3: O que é SQLAlchemy?",
                option_0="Um ORM para Python",
                option_1="Um compilador C",
                option_2="Um servidor web",
                option_3="Um editor de código",
                correct_answer=0,
                explanation="SQLAlchemy é um ORM e toolkit SQL em Python.",
                topics=["SQLAlchemy", "Banco de Dados"],
                difficulty="hard",
            ),
        ]
        self.generated_set = GeneratedQuestionSet(questions=self.raw_questions)

    def test_save_generated_questions_batch_reload_and_order_preservation(self):
        """
        Testa se:
        - As questões são adicionadas e commitadas.
        - db.refresh() NUNCA é chamado (0 chamadas individuais).
        - Exatamente UMA consulta de seleção em lote ocorre após o commit.
        - A ordem das questões retornadas preserva a ordem exata de entrada,
          mesmo se o banco retornar os registros em ordem diferente.
        """
        db = MagicMock()
        added_questions = []

        def fake_add(q):
            # Garante que o objeto tenha um id simulando a persistência
            if not getattr(q, "id", None):
                q.id = uuid4()
            added_questions.append(q)

        db.add.side_effect = fake_add

        call_order = []
        db.flush.side_effect = lambda: call_order.append("flush")
        db.commit.side_effect = lambda: call_order.append("commit")

        def fake_scalars(statement):
            call_order.append("scalars")
            # Simula o banco retornando as questões em ordem reversa para testar a reordenação
            mock_result = MagicMock()
            mock_result.all.return_value = list(reversed(added_questions))
            return mock_result

        db.scalars.side_effect = fake_scalars

        result = save_generated_questions(
            material_id=self.material_id,
            generated_questions=self.generated_set,
            db=db,
        )

        # 1. Verifica atributos esperados das questões salvas
        self.assertEqual(len(result), 3)
        self.assertEqual(len(added_questions), 3)

        for original, saved in zip(self.raw_questions, result):
            self.assertEqual(saved.material_id, self.material_id)
            self.assertEqual(saved.question_text, original.question_text)
            self.assertEqual(saved.correct_answer, original.correct_answer)
            self.assertEqual(saved.explanation, original.explanation)
            self.assertEqual(saved.topics, original.topics)
            self.assertEqual(saved.difficulty, original.difficulty)
            self.assertEqual(
                saved.options,
                {
                    "0": original.option_0,
                    "1": original.option_1,
                    "2": original.option_2,
                    "3": original.option_3,
                },
            )

        # 2. Verifica a ordem exata de entrada
        expected_ids = [q.id for q in added_questions]
        result_ids = [q.id for q in result]
        self.assertEqual(result_ids, expected_ids)

        # 3. O número de chamadas a db.refresh() deve ser ZERO
        db.refresh.assert_not_called()

        # 4. Deve haver flush, commit e exatamente UMA consulta em lote após o commit
        db.flush.assert_called_once()
        db.commit.assert_called_once()
        db.scalars.assert_called_once()
        self.assertEqual(call_order, ["flush", "commit", "scalars"])

    def test_save_generated_questions_empty_list(self):
        """
        Testa o comportamento quando a lista de questões geradas está vazia.
        """
        db = MagicMock()
        empty_set = MagicMock()
        empty_set.questions = []

        result = save_generated_questions(
            material_id=self.material_id,
            generated_questions=empty_set,
            db=db,
        )

        self.assertEqual(result, [])
        db.add.assert_not_called()
        db.flush.assert_not_called()
        db.commit.assert_not_called()
        db.refresh.assert_not_called()
        db.scalars.assert_not_called()


if __name__ == "__main__":
    unittest.main()
