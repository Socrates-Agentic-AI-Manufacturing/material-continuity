"""Bounded subprocess PDF reader. No OCR, links, scripts or network execution."""

import io
import json
import subprocess
import sys

MAX_PDF_BYTES = 2 * 1024 * 1024
MAX_PAGES = 20
MAX_TEXT = 80_000
PARSER_VERSION = "pypdf-pages-v1"


class DocumentError(ValueError):
    pass


def parse_pdf(payload):
    if not isinstance(payload, bytes) or not payload.startswith(b"%PDF-") or len(payload) > MAX_PDF_BYTES:
        raise DocumentError("PDF_INVALID_OR_TOO_LARGE")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "services.documents.parser"], input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False,
        )
    except subprocess.TimeoutExpired:
        raise DocumentError("PDF_PARSE_TIMEOUT") from None
    if result.returncode or len(result.stdout) > MAX_TEXT * 8:
        raise DocumentError("PDF_PARSE_FAILED")
    response = json.loads(result.stdout)
    if "error" in response:
        raise DocumentError(response["error"])
    return response["pages"]


def read_pages(payload):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise DocumentError("PDF_PARSER_UNAVAILABLE") from None
    reader = PdfReader(io.BytesIO(payload), strict=True)
    if reader.is_encrypted:
        raise DocumentError("PDF_ENCRYPTED")
    if not 1 <= len(reader.pages) <= MAX_PAGES:
        raise DocumentError("PDF_PAGE_LIMIT")
    pages = []
    for page in reader.pages:
        contents = page.get_contents()
        if contents is not None and len(contents.get_data()) > 1_048_576:
            raise DocumentError("PDF_CONTENT_LIMIT")
        text = page.extract_text() or ""
        pages.append(text)
        if sum(map(len, pages)) > MAX_TEXT:
            raise DocumentError("PDF_TEXT_LIMIT")
    if any(len(text.strip()) < 20 for text in pages):
        # A partially unreadable document is not a fully processed document.
        raise DocumentError("PDF_NEEDS_OCR_OR_TEXT")
    return pages


if __name__ == "__main__":
    try:
        data = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES or not data.startswith(b"%PDF-"):
            raise DocumentError("PDF_INVALID_OR_TOO_LARGE")
        print(json.dumps({"pages": read_pages(data)}))
    except DocumentError as error:
        print(json.dumps({"error": str(error)}))
    except Exception:
        print(json.dumps({"error": "PDF_PARSE_FAILED"}))
