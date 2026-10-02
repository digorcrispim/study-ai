from backend.services.openai_service import client, MODEL
from backend.services.ollama_service import (
    generate_with_ollama,
    review_with_ollama,
)
from backend.services.ai_schemas import (
    GeneratedQuestionSet,
    QuestionQualityReviewSet,
)


def generate_questions(
    material_title: str,
    raw_text: str,
    number_of_questions: int = 5,
    topic: str = "Geral",
    difficulty: str = "medium",
    objective: str = "Garantir a fixação dos conceitos fundamentais do material.",
) -> GeneratedQuestionSet:
    prompt = f"""
Você é um gerador de questões para uma plataforma de estudos.

Material:
{material_title}

Conteúdo do material:
{raw_text}

Tópico específico:
{topic}

Dificuldade desejada:
{difficulty}

Objetivo pedagógico:
{objective}

Tarefa:
Gere exatamente {number_of_questions} questões de múltipla escolha sobre o tópico "{topic}".

Regras ESTRITAS de Formatação JSON:
Você deve retornar UM ÚNICO objeto JSON válido, sem markdown, sem texto extra (nem mesmo ```json), seguindo EXATAMENTE esta estrutura de schema:
{{
  "questions": [
    {{
      "question_text": "O enunciado da pergunta aqui",
      "option_0": "Texto da alternativa A",
      "option_1": "Texto da alternativa B",
      "option_2": "Texto da alternativa C",
      "option_3": "Texto da alternativa D",
      "correct_answer": 0,
      "explanation": "Explicação detalhada do porquê esta é a correta, baseada no material.",
      "topics": ["{topic}"],
      "difficulty": "{difficulty}"
    }}
  ]
}}

Regras de Conteúdo:
1. Baseie-se exclusivamente no conteúdo fornecido.
2. "correct_answer" deve ser um INTEIRO de 0 a 3, representando o índice da alternativa correta.
3. As chaves das alternativas DEVEM ser exatamente "option_0", "option_1", "option_2", "option_3" (strings).
4. "topics" deve ser uma lista de strings, contendo pelo menos o tópico "{topic}".
5. "difficulty" deve ser exatamente "{difficulty}" (easy, medium ou hard).
6. Não invente informações que não estejam sustentadas pelo material.
"""

    try:
        response = client.responses.parse(
            model=MODEL,
            input=prompt,
            text_format=GeneratedQuestionSet,
        )

        if response.output_parsed is None:
            raise RuntimeError("A IA não retornou questões estruturadas.")

        generated = response.output_parsed
    except Exception:
        generated = generate_with_ollama(prompt)

    return validate_generated_questions(generated)


def save_generated_questions(
    material_id,
    generated_questions,
    db,
):
    from sqlalchemy import select
    from backend.models.entities import Question

    saved_questions = []

    for generated in generated_questions.questions:
        question = Question(
            material_id=material_id,
            question_text=generated.question_text,
            options={
                "0": generated.option_0,
                "1": generated.option_1,
                "2": generated.option_2,
                "3": generated.option_3,
            },
            correct_answer=generated.correct_answer,
            explanation=generated.explanation,
            topics=generated.topics,
            difficulty=generated.difficulty,
        )

        db.add(question)
        saved_questions.append(question)

    if not saved_questions:
        return []

    db.flush()
    db.commit()

    question_ids = [q.id for q in saved_questions]

    reloaded_questions = db.scalars(
        select(Question).where(Question.id.in_(question_ids))
    ).all()

    id_to_question = {q.id: q for q in reloaded_questions}
    return [id_to_question[q_id] for q_id in question_ids]


def validate_generated_questions(generated_questions):
    valid_difficulties = {"easy", "medium", "hard"}

    for index, question in enumerate(generated_questions.questions, start=1):
        options = [
            question.option_0.strip(),
            question.option_1.strip(),
            question.option_2.strip(),
            question.option_3.strip(),
        ]

        if len(options) != 4:
            raise ValueError(
                f"Questão {index}: é necessário ter exatamente 4 alternativas."
            )

        if any(not option for option in options):
            raise ValueError(
                f"Questão {index}: todas as alternativas precisam estar preenchidas."
            )

        if len(set(options)) != 4:
            raise ValueError(
                f"Questão {index}: as alternativas precisam ser diferentes."
            )

        if question.correct_answer not in range(4):
            raise ValueError(
                f"Questão {index}: resposta correta inválida."
            )

        if not question.question_text.strip():
            raise ValueError(
                f"Questão {index}: enunciado vazio."
            )

        if not question.explanation.strip():
            raise ValueError(
                f"Questão {index}: explicação vazia."
            )

        if not question.topics:
            raise ValueError(
                f"Questão {index}: é necessário informar pelo menos um tópico."
            )

        if question.difficulty not in valid_difficulties:
            raise ValueError(
                f"Questão {index}: dificuldade inválida."
            )

    return generated_questions



def review_generated_questions(
    material_title: str,
    raw_text: str,
    generated_questions: GeneratedQuestionSet,
) -> QuestionQualityReviewSet:
    questions_text = []

    for index, question in enumerate(
        generated_questions.questions,
        start=1,
    ):
        questions_text.append(
            f"""
Questão {index}:
Enunciado: {question.question_text}
Alternativa 0: {question.option_0}
Alternativa 1: {question.option_1}
Alternativa 2: {question.option_2}
Alternativa 3: {question.option_3}
Resposta correta indicada: {question.correct_answer}
Explicação: {question.explanation}
Tópicos: {", ".join(question.topics)}
Dificuldade: {question.difficulty}
"""
        )

    num_questions = len(generated_questions.questions)

    prompt = f"""
Você é um avaliador de qualidade de questões para uma plataforma de estudos.

Material:
{material_title}

Conteúdo original:
{raw_text}

Tarefa:
Avalie cada questão abaixo exclusivamente com base no conteúdo original.
Você deve avaliar exatamente {num_questions} questão(ões), gerando uma avaliação para cada questão na mesma ordem.

Regras ESTRITAS de Formatação JSON:
Você deve retornar UM ÚNICO objeto JSON válido, sem markdown e sem texto extra.

A raiz do JSON DEVE possuir exatamente a chave "reviews".
A chave "reviews" DEVE conter um array.
O array "reviews" DEVE conter exatamente {num_questions} objeto(s).

Estrutura obrigatória:
{{
  "reviews": [
    {{
      "supported_by_material": true,
      "single_correct_answer": true,
      "clear_and_unambiguous": true,
      "plausible_distractors": true,
      "is_approved": true,
      "reason": "Explicação breve da decisão."
    }}
  ]
}}

Regras de Avaliação:
1. Para cada questão:
   - supported_by_material: avalie se a questão e a resposta correta são sustentadas pelo material.
   - single_correct_answer: verifique se existe uma única alternativa correta.
   - clear_and_unambiguous: verifique se o enunciado é claro e não ambíguo.
   - plausible_distractors: verifique se as alternativas incorretas são plausíveis.
   - is_approved: use true somente quando todos os critérios necessários forem atendidos.
   - reason: explique brevemente a decisão com base no material.

2. A ordem das avaliações DEVE corresponder exatamente à ordem das questões recebidas.

3. Não adicione campos além dos especificados.

Questões para avaliação:
{"".join(questions_text)}
"""

    try:
        response = client.responses.parse(
            model=MODEL,
            input=prompt,
            text_format=QuestionQualityReviewSet,
        )

        if response.output_parsed is None:
            raise RuntimeError(
                "A IA não retornou a avaliação das questões."
            )

        review_set = response.output_parsed
    except Exception:
        review_set = review_with_ollama(prompt)

    if len(review_set.reviews) != len(
        generated_questions.questions
    ):
        raise RuntimeError(
            "A IA retornou uma quantidade de avaliações diferente "
            "da quantidade de questões."
        )

    return review_set


def filter_approved_questions(
    generated_questions,
    review_set,
):
    if len(generated_questions.questions) != len(review_set.reviews):
        raise RuntimeError(
            "A quantidade de avaliações não corresponde "
            "à quantidade de questões."
        )

    approved_questions = [
        question
        for question, review in zip(
            generated_questions.questions,
            review_set.reviews,
        )
        if review.is_approved
    ]

    if not approved_questions:
        raise ValueError(
            "Nenhuma questão foi aprovada pela validação de qualidade."
        )

    return GeneratedQuestionSet(
        questions=approved_questions
    )
def generate_adaptive_questions(
    material_title: str,
    raw_text: str,
    topic: str,
    difficulty: str,
    learning_goal: str,
    number_of_questions: int = 3,
) -> GeneratedQuestionSet:
    """
    Gera questões adaptativas focadas em um tópico específico.

    learning_goal:
        - "reinforce" -> reforça um conteúdo em que o estudante teve dificuldade.
        - "deepen" -> aprofunda um conteúdo em que o estudante demonstrou domínio.
    """

    if learning_goal not in {"reinforce", "deepen"}:
        raise ValueError(
            "learning_goal deve ser 'reinforce' ou 'deepen'."
        )

    valid_difficulties = {"easy", "medium", "hard"}

    if difficulty not in valid_difficulties:
        raise ValueError(
            "difficulty deve ser 'easy', 'medium' ou 'hard'."
        )

    if not topic.strip():
        raise ValueError("O tópico não pode estar vazio.")

    if learning_goal == "reinforce":
        objective = """
        O estudante apresentou dificuldade neste tópico.
        As questões devem reforçar os conceitos fundamentais,
        esclarecer possíveis confusões e trabalhar a compreensão
        progressivamente.
        """
    else:
        objective = """
        O estudante respondeu corretamente a uma questão deste tópico.
        As questões devem aprofundar o conhecimento, exigir maior
        capacidade de interpretação, relação entre conceitos e aplicação
        do conteúdo.
        """

    prompt = f"""
Você é um gerador de questões para uma plataforma de estudos.

Material:
{material_title}

Conteúdo do material:
{raw_text}

Tópico específico:
{topic}

Dificuldade desejada:
{difficulty}

Objetivo pedagógico:
{objective}

Tarefa:
Gere exatamente {number_of_questions} questões de múltipla escolha sobre o tópico "{topic}".

Regras ESTRITAS de Formatação JSON:
Você deve retornar UM ÚNICO objeto JSON válido, sem markdown, sem texto extra (nem mesmo ```json), seguindo EXATAMENTE esta estrutura de schema:
{{
  "questions": [
    {{
      "question_text": "O enunciado da pergunta aqui",
      "option_0": "Texto da alternativa A",
      "option_1": "Texto da alternativa B",
      "option_2": "Texto da alternativa C",
      "option_3": "Texto da alternativa D",
      "correct_answer": 0,
      "explanation": "Explicação detalhada do porquê esta é a correta, baseada no material.",
      "topics": ["{topic}"],
      "difficulty": "{difficulty}"
    }}
  ]
}}

Regras de Conteúdo:
1. Baseie-se exclusivamente no conteúdo fornecido.
2. "correct_answer" deve ser um INTEIRO de 0 a 3, representando o índice da alternativa correta.
3. As chaves das alternativas DEVEM ser exatamente "option_0", "option_1", "option_2", "option_3" (strings).
4. "topics" deve ser uma lista de strings, contendo pelo menos o tópico "{topic}".
5. "difficulty" deve ser exatamente "{difficulty}" (easy, medium ou hard).
6. Não invente informações que não estejam sustentadas pelo material.
"""

    try:
        response = client.responses.parse(
            model=MODEL,
            input=prompt,
            text_format=GeneratedQuestionSet,
        )

        if response.output_parsed is None:
            raise RuntimeError(
                "A IA não retornou questões adaptativas estruturadas."
            )

        raw_generated = response.output_parsed
    except Exception:
        raw_generated = generate_with_ollama(prompt)

    if len(raw_generated.questions) != number_of_questions:
        raise ValueError(
            f"A IA retornou {len(raw_generated.questions)} "
            f"questão(ões), mas eram esperadas {number_of_questions}."
        )

    generated_questions = validate_generated_questions(
        raw_generated
    )

    review_set = review_generated_questions(
        material_title=material_title,
        raw_text=raw_text,
        generated_questions=generated_questions,
    )

    approved_questions = filter_approved_questions(
        generated_questions=generated_questions,
        review_set=review_set,
    )

    for index, question in enumerate(
        approved_questions.questions,
        start=1,
    ):
        if question.difficulty != difficulty:
            raise ValueError(
                f"Questão adaptativa {index}: "
                f"a dificuldade retornada foi "
                f"'{question.difficulty}', mas era esperada "
                f"'{difficulty}'."
            )

        if topic not in question.topics:
            raise ValueError(
                f"Questão adaptativa {index}: "
                f"o tópico '{topic}' não foi informado."
            )

    return approved_questions