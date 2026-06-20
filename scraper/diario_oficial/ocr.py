"""
Extração de texto de PDFs: tenta texto nativo (PyMuPDF), faz OCR com Tesseract
se o PDF for escaneado (poucas ou nenhuma camada de texto detectada).
"""
import hashlib
import sys

import fitz  # PyMuPDF


_MIN_CHARS_POR_PAGINA = 80  # abaixo disso considera a página sem texto


def pdf_para_texto(pdf_bytes: bytes) -> tuple[str, bool]:
    """
    Extrai texto de um PDF.

    Retorna (texto, usou_ocr).
    Tenta texto nativo primeiro — mais rápido e barato.
    Se mais da metade das páginas não tiver texto legível, usa Tesseract.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_paginas = len(doc)
    partes_nativas: list[str] = []
    paginas_vazias = 0

    for page in doc:
        texto = page.get_text().strip()
        if len(texto) < _MIN_CHARS_POR_PAGINA:
            paginas_vazias += 1
        else:
            partes_nativas.append(texto)

    doc.close()

    usa_ocr = paginas_vazias > total_paginas / 2
    if usa_ocr:
        print(
            f"[OCR] {paginas_vazias}/{total_paginas} páginas sem texto — usando Tesseract.",
            file=sys.stderr,
        )
        return _ocr_tesseract(pdf_bytes), True

    return "\n\n".join(partes_nativas), False


def _ocr_tesseract(pdf_bytes: bytes) -> str:
    """Converte páginas do PDF para imagem e extrai texto com Tesseract."""
    try:
        import pdf2image
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "Instale pdf2image e pytesseract para OCR. "
            "Tesseract e Poppler também precisam estar no PATH."
        ) from exc

    imagens = pdf2image.convert_from_bytes(pdf_bytes, dpi=300)
    partes: list[str] = []
    for i, img in enumerate(imagens, 1):
        texto = pytesseract.image_to_string(img, lang="por")
        if texto.strip():
            partes.append(texto.strip())
        print(f"[OCR] Página {i}/{len(imagens)} processada.", file=sys.stderr)

    return "\n\n".join(partes)


def pdf_hash(pdf_bytes: bytes) -> str:
    """SHA-256 do conteúdo binário do PDF — usado para deduplicação."""
    return hashlib.sha256(pdf_bytes).hexdigest()
