from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")

if not endpoint:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT não configurado.")

if not deployment_name:
    raise RuntimeError("AZURE_OPENAI_DEPLOYMENT não configurado.")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

client = OpenAI(
    base_url=endpoint,
    api_key=token_provider,
)

MODEL = deployment_name


def generate_text(prompt: str) -> str:
    response = client.responses.create(
        model=MODEL,
        input=prompt,
    )

    return response.output_text
