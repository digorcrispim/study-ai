"""Serviço de transcrição de vídeos usando Faster-Whisper."""

import os
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel


def _resolve_device() -> tuple[str, str]:
    """Decide device e compute_type conforme a GPU realmente disponível.

    Usa CUDA somente quando o ctranslate2 (engine do faster-whisper) reporta
    pelo menos uma GPU. Caso contrário, cai para CPU. Isso evita que o modelo
    quebre em runtime ao forçar 'cuda' num host sem GPU, e habilita a GPU
    automaticamente quando o backend roda num host com CUDA.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            print("🚀 GPU CUDA detectada: usando device='cuda' (float16).")
            return "cuda", "float16"
    except Exception as exc:
        print(f"Detecção de GPU falhou ({exc}); usando CPU.")

    print("GPU não disponível; usando device='cpu' (int8).")
    return "cpu", "int8"


def extract_text_from_video(file_bytes: bytes, filename: str = "video.mp4") -> str:
    """
    Extrai texto de arquivo de vídeo usando transcrição de áudio.

    Args:
        file_bytes: Bytes do arquivo de vídeo
        filename: Nome original do arquivo (para extensão)

    Returns:
        Texto transcrito do áudio do vídeo

    Raises:
        ValueError: Se a transcrição falhar ou o texto for muito curto
    """
    # Determinar extensão do arquivo
    ext = Path(filename).suffix.lower()
    if ext not in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
        raise ValueError(f"Formato de vídeo não suportado: {ext}")

    # Salvar vídeo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_video:
        tmp_video.write(file_bytes)
        tmp_video_path = tmp_video.name

    try:
        # Provedor primário: Azure Speech-to-Text. Se não configurado,
        # falhar, ou devolver texto insuficiente, cai para o Whisper local.
        from .azure_speech_service import transcribe_with_azure_speech

        azure_text = transcribe_with_azure_speech(tmp_video_path)
        if azure_text and len(azure_text.strip()) >= 50:
            return azure_text.strip()

        print(
            "⚠️ Azure Speech indisponível ou texto insuficiente; "
            "usando Whisper local..."
        )
        transcript = _transcribe_with_whisper(tmp_video_path)

        # Validar tamanho do texto
        if len(transcript.strip()) < 50:
            raise ValueError(
                "O vídeo parece estar sem áudio ou com muito pouco "
                "conteúdo falado."
            )

        return transcript.strip()

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Falha na transcrição do vídeo: {exc}")

    finally:
        # Limpar arquivo temporário
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)


def _transcribe_with_whisper(video_path: str) -> str:
    """Transcreve um arquivo de vídeo/áudio com faster-whisper (fallback local)."""
    # Device/compute_type resolvidos conforme a GPU realmente disponível
    # (CUDA se houver, senão CPU/int8).
    device, compute_type = _resolve_device()
    model = WhisperModel("small", device=device, compute_type=compute_type)

    segments, info = model.transcribe(video_path, beam_size=5, language="pt")
    return " ".join([segment.text for segment in segments]).strip()
