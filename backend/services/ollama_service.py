import requests
from backend.services.ai_schemas import GeneratedQuestionSet, QuestionQualityReviewSet

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"

def generate_with_ollama(prompt: str) -> GeneratedQuestionSet:
    """Gera questões usando Ollama local com formatação JSON forçada."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    # Timeout de 120s para dar tempo ao processamento local da CPU
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return GeneratedQuestionSet.model_validate_json(data["response"])

def review_with_ollama(prompt: str) -> QuestionQualityReviewSet:
    """Avalia a qualidade das questões usando Ollama local."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return QuestionQualityReviewSet.model_validate_json(data["response"])
