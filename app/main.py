"""FastAPI application factory for the backend-only logistics optimization service."""

import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# OCR fallback (optional - only needed for scanned PDFs)
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    HAS_OCR = True
    # Explicitly configure tesseract path to ensure it's found
    # regardless of environment PATH configuration
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
except ImportError:
    HAS_OCR = False

# OpenCV preprocessing for OCR (optional - improves scanned PDF quality)
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from .api.routes import router
from .config import settings
from .models.request_models import OptimizeRequest
from .services.optimization_service import optimize_request
from .table_extractor import _is_data_row, cluster_words_into_rows

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend-only CP-SAT logistics optimization service for n8n workflows.",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


class PageRows(BaseModel):
    page_number: int
    rows: List[str]
    extraction_method: str = "text_layer"


class ExtractResponse(BaseModel):
    source_filename: str
    page_width: float
    num_pages: int
    pages: List[PageRows]
    total_candidate_rows: int


DEBUG_HEADER_SAMPLE_PDF_PATH = Path("tests/sample_header.pdf")


def extract_page_rows(page) -> List[List[Dict[str, Any]]]:
    words = page.extract_words()
    return cluster_words_into_rows(words)


def _ocr_fallback_for_page(
    pdf_bytes: bytes,
    page_number: int,
    page_width_pts: float,
) -> tuple[List[str], str]:
    """
    OCR fallback for scanned/image-based PDF pages.
    
    pdfplumber can only extract from text-layer PDFs; scanned pages return
    zero words. This function re-renders the page as an image and runs
    Tesseract OCR on it, converting pixel coordinates back to PDF points
    so downstream logic doesn't need to know OCR was involved.
    
    Optimizations:
    - 300 DPI for high-quality rasterization
    - OpenCV preprocessing: grayscale + adaptive thresholding for contrast
    - PSM 6 (uniform text blocks) for table-like documents
    - Confidence threshold 50% to filter low-quality tokens
    
    Returns: (compact_row_strings, extraction_method_label)
    """
    compact_rows: List[str] = []
    extraction_method = "ocr_fallback"
    
    if not HAS_OCR:
        logger.warning(
            f"OCR not available for page {page_number}. "
            "Install pytesseract and pdf2image to enable OCR fallback."
        )
        return [], "ocr_unavailable"
    
    try:
        # Convert page to image at 300 DPI
        images = convert_from_bytes(
            pdf_bytes,
            first_page=page_number,
            last_page=page_number,
            dpi=300,
        )
        if not images:
            return [], "ocr_failed"
        
        image = images[0]
        
        # Preprocess image for better OCR quality (if OpenCV available)
        if HAS_OPENCV:
            # Convert PIL Image to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            # Adaptive thresholding to enhance contrast on scanned documents
            # blockSize=11 for medium detail, C=2 to adjust threshold dynamically
            cv_image = cv2.adaptiveThreshold(
                cv_image,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2,
            )
            # Convert back to PIL for pytesseract
            from PIL import Image
            image = Image.fromarray(cv_image)
        
        image_width_px = image.width
        
        # Run OCR with improved config for table-like text blocks
        ocr_df = pytesseract.image_to_data(
            image,
            config='--psm 6',  # PSM 6: assume uniform text blocks (tables)
            output_type=pytesseract.Output.DATAFRAME,
        )
        
        # Filter: drop empty/whitespace text and low confidence (50% minimum)
        ocr_df = ocr_df[ocr_df["text"].str.strip() != ""]
        ocr_df = ocr_df[ocr_df["conf"] > 50]
        
        if ocr_df.empty:
            return [], extraction_method
        
        # Convert pixel coordinates to PDF points
        scale_factor = page_width_pts / image_width_px
        
        # Build word dicts matching pdfplumber's extract_words() format
        ocr_words: List[Dict[str, Any]] = []
        for _, row in ocr_df.iterrows():
            x0_px = float(row["left"])
            top_px = float(row["top"])
            width_px = float(row["width"])
            
            word_dict = {
                "text": str(row["text"]),
                "x0": x0_px * scale_factor,
                "top": top_px * scale_factor,
                "x1": (x0_px + width_px) * scale_factor,
                "height": float(row["height"]) * scale_factor,
                "width": width_px * scale_factor,
            }
            ocr_words.append(word_dict)
        
        # Feed through existing clustering and filtering logic
        for row_words in cluster_words_into_rows(ocr_words):
            if not _is_data_row(row_words):
                continue
            sorted_words = sorted(row_words, key=lambda w: w["x0"])
            compact = " ".join(
                f"{round(word['x0'], 1)}:{word['text']}"
                for word in sorted_words
            )
            compact_rows.append(compact)
        
        return compact_rows, extraction_method
    
    except Exception as e:
        logger.warning(
            f"OCR fallback failed for page {page_number}: {str(e)}"
        )
        return [], "ocr_failed"


def row_words_to_debug(row_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "text": word["text"],
            "x0": word["x0"],
            "x1": word["x1"],
            "top": word["top"],
        }
        for word in sorted(row_words, key=lambda w: w["x0"])
    ]


@app.post("/extract-transfers", response_model=ExtractResponse)
async def extract_transfers(file: UploadFile = File(...)) -> ExtractResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()
    pages: List[PageRows] = []
    total_candidate_rows = 0
    page_width = 0.0

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page_width = pdf.pages[0].width if pdf.pages else 0.0
        for page_number, page in enumerate(pdf.pages, start=1):
            compact_rows: List[str] = []
            extraction_method = "text_layer"
            
            # Try text-layer extraction via pdfplumber
            words = page.extract_words()
            
            if not words:
                # Fallback to OCR for scanned/image-only pages
                compact_rows, extraction_method = _ocr_fallback_for_page(
                    content, page_number, page_width
                )
            else:
                # Normal text-layer extraction path
                for row_words in cluster_words_into_rows(words):
                    if not _is_data_row(row_words):
                        continue
                    total_candidate_rows += 1
                    sorted_words = sorted(row_words, key=lambda w: w["x0"])
                    compact = " ".join(
                        f"{round(word['x0'], 1)}:{word['text']}"
                        for word in sorted_words
                    )
                    compact_rows.append(compact)
            
            # Count rows from OCR fallback as well
            if extraction_method != "text_layer":
                total_candidate_rows += len(compact_rows)
            
            pages.append(PageRows(
                page_number=page_number,
                rows=compact_rows,
                extraction_method=extraction_method,
            ))

    return ExtractResponse(
        source_filename=file.filename,
        page_width=page_width,
        num_pages=len(pages),
        pages=pages,
        total_candidate_rows=total_candidate_rows,
    )


# Deprecated troubleshooting endpoint retained for diagnostics only.
@app.post("/debug-columns")
async def debug_columns(file: UploadFile = File(...)) -> Dict[str, Any]:
    content = await file.read()
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page = pdf.pages[0]
        rows = []
        for row_words in extract_page_rows(page):
            rows.append([
                {
                    "text": word["text"],
                    "x0": word["x0"],
                    "x1": word["x1"],
                    "top": word["top"],
                }
                for word in sorted(row_words, key=lambda w: w["x0"])
            ])
        return {
            "num_pages": len(pdf.pages),
            "rows": rows,
        }


# Deprecated troubleshooting endpoint retained for diagnostics only.
@app.post("/debug-detected-boundaries")
async def debug_detected_boundaries(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        all_page_rows: List[List[Dict[str, Any]]] = []
        for page in pdf.pages:
            all_page_rows.extend(extract_page_rows(page))

        page_width = pdf.pages[0].width if pdf.pages else 0.0
        row_dicts = [
            {"words": sorted(row_words, key=lambda w: w["x0"])}
            for row_words in all_page_rows
        ]
        candidate_rows = [row for row in row_dicts if _is_data_row(row.get("words", []))]

        histogram_full: Dict[int, int] = {}
        for row in candidate_rows:
            for word in row.get("words", []):
                text = str(word.get("text", "")).strip()
                if not text:
                    continue
                x0 = float(word.get("x0", 0))
                bucket = int(round(x0 / 2.0)) * 2
                if 150 <= bucket <= 420:
                    histogram_full[bucket] = histogram_full.get(bucket, 0) + 1

        histogram_150_420 = [
            {"x0": bucket, "count": count}
            for bucket, count in sorted(histogram_full.items())
            if count > 0
        ]

        candidate_row_word_windows = []
        for idx, row in enumerate(candidate_rows[:10]):
            window_words = [
                {
                    "text": word["text"],
                    "x0": word["x0"],
                    "x1": word["x1"],
                    "top": word["top"],
                }
                for word in row.get("words", [])[5:9]
            ]
            candidate_row_word_windows.append({
                "row_index": idx,
                "window_words": window_words,
            })

        return {
            "page_width": page_width,
            "num_rows": len(row_dicts),
            "num_candidate_rows": len(candidate_rows),
            "histogram_150_420": histogram_150_420,
            "candidate_row_word_windows": candidate_row_word_windows,
        }


HEADER_DEBUG_KEYWORDS = [
    "SN",
    "EMP",
    "NO",
    "NAME",
    "GRADE",
    "CURRENT",
    "LOCATION",
    "NEW",
    "FUNCTION",
    "REMARK",
]


def normalize_keyword_token(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def looks_like_header_row(words: List[Dict[str, Any]]) -> bool:
    text = " ".join([normalize_keyword_token(word["text"]) for word in words])
    matches = 0
    for keyword in HEADER_DEBUG_KEYWORDS:
        if keyword in text:
            matches += 1
        if matches >= 2:
            return True
    return False


def row_debug_info(row_index: int, row_words: List[Dict[str, Any]]) -> Dict[str, Any]:
    tops = [word["top"] for word in row_words]
    words = [
        {
            "text": word["text"],
            "x0": word["x0"],
            "x1": word["x1"],
            "top": word["top"],
        }
        for word in sorted(row_words, key=lambda w: w["x0"])
    ]
    return {
        "row_index": row_index,
        "top_min": min(tops) if tops else None,
        "top_avg": sum(tops) / len(tops) if tops else None,
        "looks_like_header": looks_like_header_row(row_words),
        "words": words,
    }


@app.post("/debug-header-row")
async def debug_header_row(
    file: Optional[UploadFile] = File(None),
    pdf_path: Optional[str] = None,
) -> Dict[str, Any]:
    if file is not None:
        content = await file.read()
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            page = pdf.pages[0]
            page_rows = extract_page_rows(page)
            rows = [row_debug_info(i, row) for i, row in enumerate(page_rows[:15])]
            return {
                "source": file.filename,
                "num_pages": len(pdf.pages),
                "rows": rows,
            }

    path = Path(pdf_path) if pdf_path else DEBUG_HEADER_SAMPLE_PDF_PATH
    if not path or not path.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"No debug PDF found. Provide a valid ?pdf_path=... or place a sample PDF at "
                f"{DEBUG_HEADER_SAMPLE_PDF_PATH}"
            ),
        )
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        page_rows = extract_page_rows(page)
        rows = [row_debug_info(i, row) for i, row in enumerate(page_rows[:15])]
        return {
            "source": str(path),
            "num_pages": len(pdf.pages),
            "rows": rows,
        }


@app.post("/debug-pdf")
async def debug_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    content = await file.read()
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page = pdf.pages[0]
        return {
            "num_pages": len(pdf.pages),
            "lines_detected": len(page.lines),
            "rects_detected": len(page.rects),
            "words_detected": len(page.extract_words()),
            "raw_text_sample": (page.extract_text() or "")[:500],
        }


def read_root() -> Dict[str, Any]:
    """Compatibility wrapper for the old root endpoint."""
    return {
        "message": "Welcome to the PC Logistics Optimization Engine",
        "version": settings.VERSION,
        "status": "active",
    }


def health_check() -> Dict[str, Any]:
    """Compatibility wrapper for the previous health endpoint."""
    from .api.routes import health_check as health_route

    return health_route()


def optimize_pc_allocation(payload: OptimizeRequest) -> Any:
    """Compatibility wrapper for the previous optimize endpoint handler."""
    return optimize_request(payload)
