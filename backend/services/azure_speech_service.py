"""Serviço de transcrição de alta performance usando Azure Speech-to-Text."""

import os
import subprocess
import tempfile
import azure.cognitiveservices.speech as speechsdk
from typing import Optional


def transcribe_with_azure_speech(input_file_path: str) -> Optional[str]:
    """
    Transcreve áudio usando Azure Speech-to-Text.
    Converte para WAV 16kHz mono antes do processamento para garantir
    compatibilidade do SDK.
    """
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION", "eastus")

    if not speech_key or speech_key == "sua_chave_aqui":
        return None

    wav_path = None
    try:
        # 1. Converter para o formato exigido pelo Azure Speech SDK
        # (WAV, 16kHz, mono).
        wav_path = tempfile.mktemp(suffix=".wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_file_path,
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        # 2. Configurar Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=service_region
        )
        speech_config.speech_recognition_language = "pt-BR"

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        # 3. Executar reconhecimento
        result = speech_recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        return None

    except Exception:
        return None

    finally:
        # 4. Limpeza: remover o arquivo WAV temporário
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
