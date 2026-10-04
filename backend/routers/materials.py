import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal
from backend.models.entities import Material, Question
from backend.services.pdf_service import extract_text_from_document

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
from backend.services.ai_question_service import (
    generate_questions,
    review_generated_questions,
    filter_approved_questions,
    save_generated_questions,
)
from backend.models.schemas import (
    MaterialCreate,
    MaterialResponse,
    MaterialTextUpdate,
    QuestionGenerationRequest,
    QuestionResponse,
)

router = APIRouter(prefix="/materials", tags=["Materiais"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_material(
    material_data: MaterialCreate,
    db: Session = Depends(get_db),
):
    material = Material(
        title=material_data.title,
        type=material_data.type,
        storage_path=material_data.storage_path,
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    return material


@router.get("", response_model=list[MaterialResponse])
def list_materials(db: Session = Depends(get_db)):
    statement = select(Material).order_by(Material.created_at.desc())
    return db.scalars(statement).all()


@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(
    material_id: UUID,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)

    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material não encontrado.",
        )

    return material



@router.patch("/{material_id}/text")
def update_material_text(
    material_id: UUID,
    material_data: MaterialTextUpdate,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)

    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material não encontrado.",
        )

    material.raw_text = material_data.raw_text

    db.commit()
    db.refresh(material)

    return {
        "id": material.id,
        "title": material.title,
        "status": "text_updated",
    }



@router.post(
    "/{material_id}/generate-questions",
    response_model=list[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_material_questions(
    material_id: UUID,
    generation_data: QuestionGenerationRequest,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)

    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material não encontrado.",
        )

    if not material.raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O material ainda não possui texto para análise.",
        )

    # Cache: se já existem questões para este material, retorna as existentes
    # em vez de gerar novamente.
    existing_questions = db.scalars(
        select(Question).where(Question.material_id == material_id)
    ).all()
    if existing_questions:
        return existing_questions

    generated_questions = generate_questions(
        material_title=material.title,
        raw_text=material.raw_text,
        number_of_questions=generation_data.number_of_questions,
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

    return save_generated_questions(
        material_id=material.id,
        generated_questions=approved_questions,
        db=db,
    )



SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        "docx"
    ),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        "xlsx"
    ),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
        "pptx"
    ),
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "video/mp4": "mp4",
    "video/x-matroska": "mkv",
    "video/x-msvideo": "avi",
    "video/quicktime": "mov",
    "video/webm": "webm",
}


@router.post(
    "/upload-pdf",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content_type = file.content_type

    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "O arquivo enviado precisa ser PDF, TXT, DOCX ou vídeo "
                "(MP4, MKV, AVI, MOV, WEBM)."
            ),
        )

    file_bytes = await file.read()

    try:
        raw_text = extract_text_from_document(
            file_bytes, content_type, file.filename or "document"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível extrair o texto do documento: {exc}",
        )

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível extrair texto deste documento.",
        )

    material_id = uuid.uuid4()
    file_ext = SUPPORTED_CONTENT_TYPES[content_type]
    material_type = "video" if content_type.startswith("video/") else file_ext
    storage_path = f"uploads/{material_id}.{file_ext}"
    (UPLOAD_DIR / f"{material_id}.{file_ext}").write_bytes(file_bytes)

    material = Material(
        id=material_id,
        title=title,
        type=material_type,
        storage_path=storage_path,
        raw_text=raw_text,
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    return material


@router.get("/{material_id}/download")
def download_material(
    material_id: UUID,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)

    if material is None or not material.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não disponível para download",
        )

    file_path = Path(__file__).parent.parent / material.storage_path

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado no disco",
        )

    return FileResponse(
        path=file_path,
        filename=f"{material.title}.{file_path.suffix[1:]}",
        media_type="application/octet-stream",
    )
