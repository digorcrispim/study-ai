"""Ingestão em lote de materiais de estudo a partir de uma pasta local.

Varre uma pasta (recursivamente), identifica arquivos suportados
(PDF, TXT, DOCX, MP4, MKV, AVI, MOV, WEBM), extrai o texto (ou transcreve
vídeo), cria registros Material no banco e, opcionalmente, gera questões.

Reutiliza as funções já existentes do backend:
  - extract_text_from_document (backend.services.pdf_service)
  - generate_questions / review_generated_questions /
    filter_approved_questions / save_generated_questions
    (backend.services.ai_question_service)

Este script NÃO substitui o upload via UI; é uma forma complementar de
ingestão em lote. Nenhuma entidade, migration ou endpoint é alterado.

Uso:
    backend/venv/bin/python backend/scripts/ingest_folder.py <pasta>
    backend/venv/bin/python backend/scripts/ingest_folder.py <pasta> --dry-run
    backend/venv/bin/python backend/scripts/ingest_folder.py <pasta> --type pdf,txt
    backend/venv/bin/python backend/scripts/ingest_folder.py <pasta> --no-questions
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2])
)

from sqlalchemy import select

from backend.models.database import SessionLocal
from backend.models.entities import Material
from backend.services.pdf_service import extract_text_from_document
from backend.services.ai_question_service import (
    generate_questions,
    review_generated_questions,
    filter_approved_questions,
    save_generated_questions,
)


SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}

# Diretório onde os arquivos originais são armazenados (mesmo do upload UI).
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"

DEFAULT_NUMBER_OF_QUESTIONS = 5


def material_type_for(ext: str) -> str:
    """Mapeia a extensão para o Material.type usado no restante do sistema."""
    content_type = SUPPORTED_EXTENSIONS[ext]
    if content_type.startswith("video/"):
        return "video"
    return ext.lstrip(".")


def generate_questions_for_material(material, db) -> int:
    """Gera, revisa, filtra e persiste questões para um material.

    Reutiliza o mesmo pipeline do endpoint existente de geração.
    Retorna a quantidade de questões aprovadas/persistidas.
    """
    generated_questions = generate_questions(
        material_title=material.title,
        raw_text=material.raw_text,
        number_of_questions=DEFAULT_NUMBER_OF_QUESTIONS,
    )

    review_set = review_generated_questions(
        material_title=material.title,
        raw_text=material.raw_text,
        generated_questions=generated_questions,
    )

    approved_questions = filter_approved_questions(
        generated_questions=generated_questions,
        review_set=review_set,
    )

    saved = save_generated_questions(
        material_id=material.id,
        generated_questions=approved_questions,
        db=db,
    )

    return len(saved)


def find_supported_files(folder: Path, type_filter: set[str] | None) -> list[Path]:
    """Encontra recursivamente todos os arquivos suportados na pasta."""
    files = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        if type_filter is not None and ext.lstrip(".") not in type_filter:
            continue
        files.append(path)
    return files


def material_exists(db, title: str) -> bool:
    """Verifica se já existe um Material com o mesmo título (anti-duplicata)."""
    existing = db.scalars(
        select(Material).where(Material.title == title)
    ).first()
    return existing is not None


def process_file(
    index: int,
    total: int,
    path: Path,
    db,
    generate: bool,
) -> str:
    """Processa um único arquivo. Retorna 'ok', 'skipped' ou 'failed'."""
    ext = path.suffix.lower()
    title = path.stem
    print(f"[{index}/{total}] {path.name}")

    if material_exists(db, title):
        print(f"   ⏭️  ignorado (já existe material com o título '{title}')")
        return "skipped"

    try:
        content_type = SUPPORTED_EXTENSIONS[ext]
        file_bytes = path.read_bytes()

        print("   📄 extraindo texto...")
        raw_text = extract_text_from_document(
            file_bytes, content_type, path.name
        )

        if not raw_text:
            raise ValueError("Nenhum texto extraído do arquivo.")

        material_id = uuid.uuid4()
        storage_path = f"uploads/{material_id}{ext}"
        UPLOAD_DIR.mkdir(exist_ok=True)
        (UPLOAD_DIR / f"{material_id}{ext}").write_bytes(file_bytes)

        material = Material(
            id=material_id,
            title=title,
            type=material_type_for(ext),
            storage_path=storage_path,
            raw_text=raw_text,
        )
        db.add(material)
        db.commit()
        db.refresh(material)

        if generate:
            # Cache: se o material já possui questões, pula a geração.
            from backend.models.entities import Question
            from sqlalchemy import func

            existing_count = db.scalar(
                select(func.count(Question.id)).where(
                    Question.material_id == material.id
                )
            )
            if existing_count and existing_count > 0:
                print(
                    f"   ⏭️  questões já existem ({existing_count}), "
                    "pulando geração"
                )
            else:
                print("   🤖 gerando questões...")
                count = generate_questions_for_material(material, db)
                print(f"   ✅ material criado + {count} questão(ões) geradas")
        else:
            print("   ✅ material criado (sem geração de questões)")

        return "ok"

    except Exception as exc:
        db.rollback()
        print(f"   ❌ erro: {exc}")
        return "failed"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingestão em lote de materiais de estudo a partir de uma pasta."
    )
    parser.add_argument("folder", help="Caminho da pasta a processar")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista os arquivos que seriam processados, sem processar.",
    )
    parser.add_argument(
        "--type",
        default=None,
        help="Filtrar por tipo(s), separados por vírgula (ex: pdf,txt,mp4).",
    )
    parser.add_argument(
        "--no-questions",
        action="store_true",
        help="Não gerar questões automaticamente.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    folder = Path(args.folder).expanduser()

    if not folder.exists() or not folder.is_dir():
        print(f"❌ Pasta inválida: {folder}")
        sys.exit(1)

    type_filter = None
    if args.type:
        type_filter = {
            t.strip().lower().lstrip(".")
            for t in args.type.split(",")
            if t.strip()
        }

    files = find_supported_files(folder, type_filter)

    if not files:
        print("Nenhum arquivo suportado encontrado.")
        return

    print(f"Encontrados {len(files)} arquivo(s) suportado(s) em {folder}\n")

    if args.dry_run:
        print("--dry-run: nenhum arquivo será processado.\n")
        for index, path in enumerate(files, start=1):
            print(f"[{index}/{len(files)}] {path}")
        return

    generate = not args.no_questions

    processed = 0
    skipped = 0
    failed = 0

    db = SessionLocal()
    try:
        for index, path in enumerate(files, start=1):
            result = process_file(index, len(files), path, db, generate)
            if result == "ok":
                processed += 1
            elif result == "skipped":
                skipped += 1
            else:
                failed += 1
    finally:
        db.close()

    print("\n=== Resumo ===")
    print(f"   ✅ processados: {processed}")
    print(f"   ⏭️  ignorados:   {skipped}")
    print(f"   ❌ falhas:      {failed}")


if __name__ == "__main__":
    main()
