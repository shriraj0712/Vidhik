"""
Vidhik Platform - Document Parser Service (Phase 11)
===================================================
Handles secure, in-memory stream extraction and normalization for:
- Plain Text (.txt)
- Portable Document Format (.pdf) via pypdf
- Microsoft Word Document (.docx) via python-docx
- Direct pasted raw text

Enforces strict security constraints:
- Maximum upload size: 15 MB
- Extension & magic header byte validation
- In-memory processing; zero storage inside static UI folders
- Detection of non-searchable / scanned PDFs with clear diagnostic messaging
"""

import io
import re
import hashlib
from typing import Optional, Tuple
from dataclasses import dataclass
from fastapi import UploadFile, HTTPException, status
import pypdf
import docx


MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


@dataclass
class ParsedDocument:
    raw_text: str
    cleaned_text: str
    file_type: str
    file_name: str
    file_size_bytes: int
    file_hash_sha256: str
    page_count: int
    is_scanned_or_empty: bool
    warning_message: Optional[str] = None


class DocumentParserService:
    """Secure parser converting uploaded legal documents to normalized text."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalizes spacing, replaces non-printable characters, and standardizes newlines."""
        if not text:
            return ""
        # Replace carriage returns and vertical tabs
        t = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove non-printable control characters except standard tabs and newlines
        t = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", t)
        # Collapse excessive blank lines
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    @classmethod
    def parse_plain_text(cls, content: bytes, file_name: str = "document.txt") -> ParsedDocument:
        """Parses plain text with multi-encoding fallback."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
        decoded_text = ""
        for enc in encodings:
            try:
                decoded_text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not decoded_text and content:
            decoded_text = content.decode("utf-8", errors="replace")

        cleaned = cls.clean_text(decoded_text)
        file_hash = hashlib.sha256(content).hexdigest()
        is_empty = len(cleaned.strip()) == 0

        return ParsedDocument(
            raw_text=decoded_text,
            cleaned_text=cleaned,
            file_type="txt",
            file_name=file_name,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            page_count=1,
            is_scanned_or_empty=is_empty,
            warning_message="Document is empty." if is_empty else None
        )

    @classmethod
    def parse_pdf(cls, content: bytes, file_name: str = "document.pdf") -> ParsedDocument:
        """Parses PDF content using pypdf, validating magic bytes and detecting scanned pages."""
        # Magic bytes check: PDF header must begin with %PDF-
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file format. The file header does not match standard PDF specifications."
            )

        file_hash = hashlib.sha256(content).hexdigest()
        stream = io.BytesIO(content)
        extracted_pages = []
        page_count = 0

        try:
            reader = pypdf.PdfReader(stream)
            page_count = len(reader.pages)
            for idx, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted_pages.append(page_text.strip())
                except Exception:
                    continue
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to read PDF structure: {str(e)}"
            )

        raw_text = "\n\n".join(extracted_pages)
        cleaned = cls.clean_text(raw_text)

        # Detect scanned or image-based PDF (zero or extremely few characters relative to page count)
        is_scanned = (len(cleaned.strip()) < 50 and page_count > 0) or page_count == 0
        warning = None
        if is_scanned:
            warning = (
                f"Document appears to be a scanned image-based PDF ({page_count} page(s), but selectable text could not be extracted). "
                "Optical Character Recognition (OCR) is not enabled in this phase. "
                "Please provide a text-searchable digital PDF, Word (.docx), or plain text document."
            )

        return ParsedDocument(
            raw_text=raw_text,
            cleaned_text=cleaned,
            file_type="pdf",
            file_name=file_name,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            page_count=page_count,
            is_scanned_or_empty=is_scanned,
            warning_message=warning
        )

    @classmethod
    def parse_docx(cls, content: bytes, file_name: str = "document.docx") -> ParsedDocument:
        """Parses Word .docx file extracting paragraphs and tables."""
        # Magic bytes check: DOCX is a zip file, starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DOCX file format. The file does not conform to OpenXML specifications."
            )

        file_hash = hashlib.sha256(content).hexdigest()
        stream = io.BytesIO(content)
        parts = []

        try:
            doc = docx.Document(stream)
            # Extract paragraphs
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    parts.append(text)

            # Extract tables where practical
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        parts.append(" | ".join(row_cells))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to read DOCX document structure: {str(e)}"
            )

        raw_text = "\n\n".join(parts)
        cleaned = cls.clean_text(raw_text)
        is_empty = len(cleaned.strip()) == 0

        return ParsedDocument(
            raw_text=raw_text,
            cleaned_text=cleaned,
            file_type="docx",
            file_name=file_name,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            page_count=1,
            is_scanned_or_empty=is_empty,
            warning_message="Document contains no readable text." if is_empty else None
        )

    @classmethod
    def parse_raw_text_input(cls, text_input: str, document_title: Optional[str] = None) -> ParsedDocument:
        """Parses direct raw text or pasted contract clauses."""
        clean_input = cls.clean_text(text_input or "")
        file_name = (document_title or "Pasted Legal Text").strip()
        encoded = clean_input.encode("utf-8")
        file_hash = hashlib.sha256(encoded).hexdigest()
        is_empty = len(clean_input.strip()) == 0

        return ParsedDocument(
            raw_text=text_input or "",
            cleaned_text=clean_input,
            file_type="pasted_text",
            file_name=file_name,
            file_size_bytes=len(encoded),
            file_hash_sha256=file_hash,
            page_count=1,
            is_scanned_or_empty=is_empty,
            warning_message="Provided text is empty." if is_empty else None
        )

    @classmethod
    async def parse_upload(cls, file: UploadFile) -> ParsedDocument:
        """
        Validates, securely reads, and parses an uploaded file stream.
        Enforces 15 MB limit, extension validation, and format checking.
        """
        original_name = file.filename or "unknown_document"
        lower_name = original_name.lower()

        # 1. Validate file extension
        ext = None
        for allowed in ALLOWED_EXTENSIONS:
            if lower_name.endswith(allowed):
                ext = allowed
                break

        if not ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type for '{original_name}'. Only .pdf, .docx, and .txt files are supported."
            )

        # 2. Read content with size guard (max 15 MB)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of 15 MB ({len(content) / (1024 * 1024):.2f} MB received)."
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is completely empty (0 bytes)."
            )

        # 3. Dispatch to parser
        if ext == ".pdf":
            return cls.parse_pdf(content, original_name)
        elif ext == ".docx":
            return cls.parse_docx(content, original_name)
        elif ext == ".txt":
            return cls.parse_plain_text(content, original_name)

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format.")
