"""Serviço de integração com Amazon Bedrock (Claude 3.5 Sonnet)."""

import os
import json
import boto3
from typing import List, Dict


def generate_questions_with_bedrock(
    material_title: str,
    raw_text: str,
    number_of_questions: int = 5,
) -> List[Dict]:
    """
    Gera questões usando Amazon Bedrock (Claude 3.5 Sonnet).
    """
    region = os.getenv("AWS_REGION", "us-east-1")

    # Inicializa o cliente Bedrock Runtime
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
    )

    model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    prompt = f"""Você é um professor especialista em criar questões de estudo.
Material: {material_title}
Conteúdo:
{raw_text[:15000]}

Gere exatamente {number_of_questions} questões de múltipla escolha sobre o conteúdo acima.
Responda APENAS com um JSON válido no seguinte formato (sem texto adicional, sem markdown):
[
  {{
    "question": "Texto da questão",
    "options": ["Opção A", "Opção B", "Opção C", "Opção D"],
    "correct": "A",
    "explanation": "Explicação da resposta correta"
  }}
]

Requisitos:
- As questões devem ser claras e diretas.
- As opções devem ser plausíveis.
- A explicação deve ser concisa (1-2 frases).
- Responda APENAS com o JSON array, sem blocos de código markdown.
"""

    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        }
                    ],
                }
            ),
        )

        response_body = json.loads(response.get("body").read())
        response_text = response_body["content"][0]["text"]

        # Extrair JSON (removendo possíveis blocos de código markdown se o
        # modelo insistir).
        import re

        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions
        else:
            return json.loads(response_text)

    except Exception as e:
        raise ValueError(f"Falha na geração com Bedrock: {e}")
