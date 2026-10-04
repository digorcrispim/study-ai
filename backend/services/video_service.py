"""Serviço de transcrição de vídeos usando Faster-Whisper."""

import os
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel


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
        # Inicializar modelo Whisper (small é um bom equilíbrio entre
        # velocidade e precisão).
        # device="cpu" porque não assumimos GPU disponível.
        # compute_type="int8" para otimizar memória.
        model = WhisperModel("small", device="cpu", compute_type="int8")

        # Transcrever áudio do vídeo
        segments, info = model.transcribe(
            tmp_video_path, beam_size=5, language="pt"
        )

        # Concatenar todos os segmentos
        transcript = " ".join([segment.text for segment in segments])

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
