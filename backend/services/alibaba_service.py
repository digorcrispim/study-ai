"""Serviço de geração de questões usando Alibaba Cloud (Qwen) via API compatível com OpenAI."""
import os
import json
import re
from openai import OpenAI
from backend.services.ai_schemas import GeneratedQuestionSet

alibaba_client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL")
)

DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus-character")

def generate_questions_with_alibaba(
    material_title: str,
    raw_text: str,
    number_of_questions: int = 5,
    topic: str = "Geral",
    difficulty: str = "medium",
) -> GeneratedQuestionSet:
    
    if not os.getenv("DASHSCOPE_API_KEY") or "COLE_SUA_CHAVE" in os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("DASHSCOPE_API_KEY não configurada ou é um placeholder no .env")

    # Prompt ultra-compacto para evitar que o modelo corte a resposta no meio do JSON
    prompt = f"""Gere EXATAMENTE {number_of_questions} questão(ões) de múltipla escolha sobre: {topic}.
Baseie-se neste texto: "{raw_text[:1500]}"
Retorne APENAS o objeto JSON abaixo, sem markdown, sem explicações extras, de forma ultra-concisa para não estourar o limite de tokens:
{{"questions": [{{"question_text": "Enunciado curto e direto", "option_0": "Alternativa A", "option_1": "Alternativa B", "option_2": "Alternativa C", "option_3": "Alternativa D", "correct_answer": 0, "explanation": "Explicação em 1 frase", "topics": ["{topic}"], "difficulty": "{difficulty}"}}]}}"""

    try:
        response = alibaba_client.chat.completions.create(
            model=DASHSCOPE_MODEL,
            messages=[
                {"role": "system", "content": "Você é um gerador de JSON estrito. Retorne APENAS o JSON solicitado, sem nenhuma palavra extra, sem markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # Temperatura mais baixa para mais precisão e menos verbosidade
            max_tokens=2000
        )

        content = response.choices[0].message.content
        
        # Extração robusta de JSON: pega tudo entre o primeiro '{' e o último '}'
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx+1]
        else:
            # Fallback para limpeza de markdown
            content = content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            
        parsed_json = json.loads(content)
        return GeneratedQuestionSet(**parsed_json)

    except json.JSONDecodeError as e:
        raise ValueError(f"Alibaba retornou JSON inválido/truncado. Resposta bruta: {content[:300]}... | Erro: {e}")
    except Exception as e:
        raise RuntimeError(f"Falha na comunicação com Alibaba Cloud: {e}")
