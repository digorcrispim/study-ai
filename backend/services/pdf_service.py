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
