import streamlit as st
import fitz  # PyMuPDF
import pytesseract
import cv2
import numpy as np
import re
from PIL import Image

# =====================================================
# STREAMLIT CONFIG
# =====================================================

st.set_page_config(page_title="Trade Compliance OCR Test", layout="wide")
st.title("📄 Trade Compliance OCR – Extraction Test Harness")

# =====================================================
# IMAGE PREPROCESSING
# =====================================================

def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    return gray

# =====================================================
# OCR PIPELINE (PDF → TEXT)
# =====================================================

def run_ocr(uploaded_file):
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))  # ~300 DPI
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = preprocess_image(np.array(img))

        text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")

        pages.append({
            "page": page_num + 1,
            "raw_text": text.splitlines()
        })

    return pages

# =====================================================
# DOC SUBTYPE LOGIC (UNCHANGED)
# =====================================================

def doc_subtype(raw_text, doc_subtype_keyword):
    for i in doc_subtype_keyword:
        key_word = doc_subtype_keyword[i]
        for j in key_word:
            if re.search(j, str(raw_text)):
                return i.strip("d_")
    return "unknown"

# =====================================================
# MOCK WRAPPERS (REPLACE LATER)
# =====================================================

def mock_invoice_wrapper(raw_text):
    return [
        "INV-TEST",
        "Importer Name",
        "USD",
        ["HTS123"],
        ["100"],
        ["DESC"],
        ["US"],
        ["10"],
        ["PCS"],
        "TOTAL",
        ["PART-1"]
    ]

def mock_7501_wrapper(raw_text):
    return [
        "ENTRY123",
        "AWB123",
        "BROKER",
        ["HTS123"],
        ["100"],
        ["5"],
        ["1"]
    ]

# =====================================================
# JSON FORMATTERS (UNCHANGED CORE STRUCTURE)
# =====================================================

def json_format_import(result):
    obj = {"Entry Number": "", "AWB Number": "", "Broker Name": "", "LineItems": {"LineItemDetails": []}}

    for k in result:
        if k.endswith("7501"):
            obj["Entry Number"] = result[k][0]
            obj["AWB Number"] = result[k][1]
            obj["Broker Name"] = result[k][2]

        if k.endswith("invoice"):
            for i in range(len(result[k][3])):
                obj["LineItems"]["LineItemDetails"].append({
                    "HTS": result[k][3][i],
                    "Value": result[k][4][i],
                    "Description": result[k][5][i]
                })

    return obj

# =====================================================
# MAIN PROCESSOR
# =====================================================

def process_pages(pages, document_type):
    doc_subtype_keyword = {
        "d_7501": [
            "OMB APPROVAL NO",
            "ENTRY SUMMARY",
            "Form Approved OMB"
        ],
        "d_invoice": [
            "INVOICE",
            "COMMERCIAL INVOICE",
            "PROFORMA"
        ]
    }

    result = {}

    for p in pages:
        raw_text = p["raw_text"]
        subtype = doc_subtype(raw_text, doc_subtype_keyword)

        if subtype == "invoice":
            result[f"page_{p['page']}_invoice"] = mock_invoice_wrapper(raw_text)
        elif subtype == "7501":
            result[f"page_{p['page']}_7501"] = mock_7501_wrapper(raw_text)

    if document_type == "import":
        return json_format_import(result)

    return result

# =====================================================
# UI
# =====================================================

doc_type = st.selectbox("Document Type", ["import", "export", "recon", "drawback"])
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    with st.spinner("Running OCR..."):
        pages = run_ocr(uploaded_file)

    st.success(f"OCR completed: {len(pages)} pages")

    with st.spinner("Running extraction logic..."):
        output = process_pages(pages, doc_type)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Extracted JSON")
        st.json(output)

    with col2:
        st.subheader("📝 OCR Preview")
        for p in pages:
            with st.expander(f"Page {p['page']}"):
                st.text("\n".join(p["raw_text"]))
