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
