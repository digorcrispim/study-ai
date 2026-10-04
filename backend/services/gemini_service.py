"""Serviço de integração com Google Gemini API."""

import os
import google.generativeai as genai
from typing import List, Dict

from dotenv import load_dotenv
from pathlib import Path

# Carregar .env do diretório backend
load_dotenv(Path(__file__).parent.parent / ".env")


def generate_questions_with_gemini(
    material_title: str,
    raw_text: str,
    number_of_questions: int = 5,
) -> List[Dict]:
    """
    Gera questões usando Google Gemini API.

    Args:
        material_title: Título do material
        raw_text: Texto completo do material
        number_of_questions: Número de questões a gerar

    Returns:
        Lista de dicionários com questões no formato:
        [{"question": "...", "options": ["A", "B", "C", "D"],
          "correct": "A", "explanation": "..."}]

    Raises:
        ValueError: Se a API key não estiver configurada ou a geração falhar
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada")

    try:
        genai.configure(api_key=api_key)

        # Usar o alias estável do modelo Flash (rápido e eficiente).
        model = genai.GenerativeModel("gemini-flash-latest")

        prompt = f"""Você é um professor especialista em criar questões de estudo.
Material: {material_title}
Conteúdo:
{raw_text[:15000]}

Gere exatamente {number_of_questions} questões de múltipla escolha sobre o conteúdo acima.
Responda APENAS com um JSON válido no seguinte formato (sem texto adicional):
[
  {{
    "question": "Texto da questão",
    "options": ["Opção A", "Opção B", "Opção C", "Opção D"],
    "correct": "A",
    "explanation": "Explicação da resposta correta"
  }}
]

Requisitos:
- As questões devem ser claras e diretas
- As opções devem ser plausíveis
- A explicação deve ser concisa (1-2 frases)
- Responda APENAS com o JSON, sem texto adicional
"""

        response = model.generate_content(prompt)

        # Extrair JSON da resposta
        import json
        import re

        # Tentar extrair JSON da resposta
        json_match = re.search(r"\[.*\]", response.text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions
        else:
            # Tentar parse direto
            questions = json.loads(response.text)
            return questions

    except Exception as e:
        raise ValueError(f"Falha na geração com Gemini: {e}")
