"""Serviço de transcrição usando Azure Speech-to-Text."""

import os
import azure.cognitiveservices.speech as speechsdk
from typing import Optional


def transcribe_with_azure_speech(audio_file_path: str) -> Optional[str]:
    """
    Transcreve áudio usando Azure Speech-to-Text.
    Retorna o texto transcrito ou None se falhar.
    """
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION", "eastus")

    if not speech_key or speech_key == "sua_chave_aqui":
        print("⚠️ AZURE_SPEECH_KEY não configurada, pulando Azure Speech")
        return None

    try:
        # Configurar reconhecimento de áudio
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=service_region,
        )
        speech_config.speech_recognition_language = "pt-BR"

        # Configurar entrada de áudio
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

        # Criar reconhecedor
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        print("🚀 Transcrevendo com Azure Speech-to-Text...")

        # Transcrever uma vez (reconhecimento único)
        result = speech_recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"✅ Azure Speech: {len(result.text)} caracteres transcritos")
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("⚠️ Azure Speech: nenhum áudio reconhecido")
            return None
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f"⚠️ Azure Speech cancelado: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                print(f"   Erro: {cancellation.error_details}")
            return None

    except Exception as e:
        print(f"❌ Erro no Azure Speech: {e}")
        return None
