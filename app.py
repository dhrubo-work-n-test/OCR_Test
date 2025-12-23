import streamlit as st
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import json

# =========================
# OCR PREPROCESSING
# =========================

def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh

def ocr_image(img):
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(img, config=config)
    return text.splitlines()

# =========================
# OCR PIPELINE
# =========================

def run_ocr(uploaded_file):
    pages = convert_from_bytes(uploaded_file.read(), dpi=300)
    all_pages = []

    for idx, page in enumerate(pages):
        img = np.array(page)
        img = preprocess_image(img)
        raw_text = ocr_image(img)

        all_pages.append({
            "page": idx + 1,
            "raw_text": raw_text
        })

    return all_pages

# =========================
# DOCUMENT SUBTYPE
# (same logic as your lambda)
# =========================

def doc_subtype(raw_text):
    text = " ".join(raw_text)

    if any(k in text for k in ["OMB APPROVAL NO", "ENTRY SUMMARY"]):
        return "7501"
    if any(k in text for k in ["INVOICE", "Commercial Invoice", "PROFORMA"]):
        return "invoice"
    return "unknown"

# =========================
# PLACEHOLDERS FOR YOUR LOGIC
# =========================

def import_wrapper_invoice(raw_text):
    return {
        "Invoice Number": "EXTRACTED_VALUE",
        "LineItems": []
    }

def import_wrapper_7501(raw_text):
    return {
        "Entry Number": "EXTRACTED_VALUE"
    }

# =========================
# MAIN PROCESSOR
# =========================

def process_document(pages, document_type):
    result = {}

    for page in pages:
        raw_text = page["raw_text"]
        subtype = doc_subtype(raw_text)

        if subtype == "invoice":
            if document_type == "import":
                invoice = import_wrapper_invoice(raw_text)
                result[f"page_{page['page']}_invoice"] = invoice

        elif subtype == "7501":
            if document_type == "import":
                f7501 = import_wrapper_7501(raw_text)
                result[f"page_{page['page']}_7501"] = f7501

    return result

# =========================
# STREAMLIT UI
# =========================

st.set_page_config(page_title="Trade Compliance OCR", layout="wide")

st.title("📄 Trade Compliance OCR Demo")

doc_type = st.selectbox(
    "Select Document Type",
    ["import", "export", "recon", "drawback"]
)

uploaded_file = st.file_uploader(
    "Upload PDF Document",
    type=["pdf"]
)

if uploaded_file:
    with st.spinner("Running OCR..."):
        pages = run_ocr(uploaded_file)

    st.success(f"OCR completed for {len(pages)} pages")

    with st.spinner("Running extraction logic..."):
        extracted_result = process_document(pages, doc_type)

    st.subheader("📦 Extracted JSON")
    st.json(extracted_result)

    st.subheader("📝 OCR Preview")
    for p in pages:
        with st.expander(f"Page {p['page']}"):
            st.text("\n".join(p["raw_text"]))
