import io, os
from typing import Optional

def ext_from_name(name: str) -> str:
    return os.path.splitext(name)[1].lower()

def pdf_to_text(data: bytes) -> str:
    from pdfminer.high_level import extract_text
    return extract_text(io.BytesIO(data)) or ""

def docx_to_text(data: bytes) -> str:
    from docx import Document
    f = io.BytesIO(data)
    doc = Document(f)
    return "\n".join(p.text for p in doc.paragraphs)

def file_to_text(data: bytes, filename: str) -> str:
    ext = ext_from_name(filename)
    if ext == ".pdf":
        return pdf_to_text(data)
    if ext == ".docx":
        return docx_to_text(data)
    # You can add .rtf/.txt as needed. For legacy .doc use textract (optional).
    raise ValueError(f"Unsupported resume format: {ext}. Use PDF or DOCX.")
