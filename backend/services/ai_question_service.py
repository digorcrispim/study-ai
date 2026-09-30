from backend.services.openai_service import client, MODEL
from backend.services.ai_schemas import (
    GeneratedQuestionSet,
    QuestionQualityReviewSet,
)


def generate_questions(
    material_title: str,
    raw_text: str,
    number_of_questions: int = 5,
) -> GeneratedQuestionSet:
    prompt = f"""
Você é um gerador de questões para uma plataforma de estudos.

Material:
{material_title}

Conteúdo do material:
{raw_text}

Tarefa:
Gere exatamente {number_of_questions} questões de múltipla escolha
baseadas exclusivamente no conteúdo fornecido.

Regras:
- Cada questão deve ter 4 alternativas.
- Use as chaves "0", "1", "2" e "3" nas alternativas.
- "correct_answer" deve ser o índice da alternativa correta.
- A explicação deve justificar a resposta correta com base no conteúdo.
- Informe de 1 a 3 tópicos por questão.
- Use apenas estas dificuldades: easy, medium ou hard.
- Não invente informações que não estejam sustentadas pelo conteúdo.
"""

    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=GeneratedQuestionSet,
    )

    if response.output_parsed is None:
        raise RuntimeError("A IA não retornou questões estruturadas.")

    return validate_generated_questions(response.output_parsed)


def save_generated_questions(
    material_id,
    generated_questions,
    db,
):
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

    db.commit()

    for question in saved_questions:
        db.refresh(question)

    return saved_questions


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

    prompt = f"""
Você é um avaliador de qualidade de questões para uma plataforma
de estudos.

Material:
{material_title}

Conteúdo original:
{raw_text}

Avalie cada questão abaixo exclusivamente com base no conteúdo original.

Para cada questão, determine:
- supported_by_material: a questão e sua resposta correta estão
  sustentadas pelo conteúdo?
- single_correct_answer: existe uma única alternativa correta?
- clear_and_unambiguous: o enunciado é claro e não ambíguo?
- plausible_distractors: as alternativas incorretas são plausíveis?
- is_approved: a questão está adequada para entrar no banco de questões?
- reason: explique brevemente a decisão.

Uma questão só deve ser aprovada quando estiver sustentada pelo material,
tiver uma única resposta correta, for clara e tiver distratores plausíveis.

Questões para avaliação:
{"".join(questions_text)}
"""

    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=QuestionQualityReviewSet,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "A IA não retornou a avaliação das questões."
        )

    if len(response.output_parsed.reviews) != len(
        generated_questions.questions
    ):
        raise RuntimeError(
            "A IA retornou uma quantidade de avaliações diferente "
            "da quantidade de questões."
        )

    return response.output_parsed


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
Você é um gerador de questões adaptativas para uma plataforma de estudos.

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
Gere exatamente {number_of_questions} questões de múltipla escolha
sobre o tópico "{topic}".

Regras:
- Baseie-se exclusivamente no conteúdo fornecido.
- Cada questão deve ter exatamente 4 alternativas.
- Use as chaves "0", "1", "2" e "3" nas alternativas.
- "correct_answer" deve ser o índice da alternativa correta.
- A explicação deve justificar a resposta correta com base no material.
- Informe de 1 a 3 tópicos por questão.
- Use somente a dificuldade "{difficulty}".
- O tópico "{topic}" deve aparecer entre os tópicos da questão.
- Não repita simplesmente a pergunta original.
- Não invente informações que não estejam sustentadas pelo material.
"""

    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=GeneratedQuestionSet,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "A IA não retornou questões adaptativas estruturadas."
        )

    if len(response.output_parsed.questions) != number_of_questions:
        raise ValueError(
            f"A IA retornou {len(response.output_parsed.questions)} "
            f"questão(ões), mas eram esperadas {number_of_questions}."
        )

    generated_questions = validate_generated_questions(
        response.output_parsed
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