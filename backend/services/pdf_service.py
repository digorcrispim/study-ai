from io import BytesIO

from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract

MINIMUM_TEXT_LENGTH = 50


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de um PDF de forma resiliente.

    Estratégia:
      1. Tenta extração nativa com pypdf (rápida, para PDFs com texto).
      2. Se o texto nativo for vazio ou curto demais (< MINIMUM_TEXT_LENGTH),
         faz fallback para OCR (pdf2image + pytesseract), útil para PDFs
         escaneados/imagem.
      3. Se nada funcionar, lança ValueError com mensagem clara.
    """
    # 1. Tentativa nativa (pypdf)
    try:
        reader = PdfReader(BytesIO(pdf_bytes))

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            text = text.strip()

            if text:
                pages.append(text)

        native_text = "\n\n".join(pages).strip()

        if len(native_text) > MINIMUM_TEXT_LENGTH:
            return native_text
    except Exception as exc:
        print(f"Extração nativa falhou: {exc}")

    # 2. Fallback OCR (pdf2image + pytesseract)
    try:
        images = convert_from_bytes(pdf_bytes)

        ocr_pages = []

        for image in images:
            ocr_text = pytesseract.image_to_string(image, lang="por")
            ocr_text = ocr_text.strip()

            if ocr_text:
                ocr_pages.append(ocr_text)

        ocr_result = "\n\n".join(ocr_pages).strip()

        if len(ocr_result) > MINIMUM_TEXT_LENGTH:
            return ocr_result
    except Exception as exc:
        raise ValueError(
            f"Falha na extração por OCR: {exc}. "
            "Verifique se o Tesseract-OCR está instalado no sistema."
        )

    raise ValueError(
        "Não foi possível extrair texto do PDF. O arquivo pode estar "
        "vazio, corrompido ou ser uma imagem não legível."
    )


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extrai texto de arquivo .txt (decodifica como UTF-8)."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        raise ValueError(
            "Não foi possível decodificar o arquivo .txt. "
            "Verifique se está em UTF-8."
        )


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrai texto de arquivo .docx usando python-docx."""
    import io
    from docx import Document

    try:
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])

        if len(text.strip()) < MINIMUM_TEXT_LENGTH:
            raise ValueError(
                "O arquivo .docx parece estar vazio ou com muito pouco texto."
            )

        return text.strip()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Falha ao extrair texto do .docx: {exc}")


def extract_text_from_document(file_bytes: bytes, content_type: str) -> str:
    """Despacha para a função de extração correta baseada no content_type."""
    if content_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)
    elif content_type == "text/plain":
        return extract_text_from_txt(file_bytes)
    elif content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Formato de arquivo não suportado: {content_type}")
