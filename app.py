import streamlit as st
import fitz  # PyMuPDF
import re

# =====================================================
# STREAMLIT CONFIG
# =====================================================

st.set_page_config(page_title="Trade Compliance Extraction Test", layout="wide")
st.title("📄 Trade Compliance – Extraction Logic Test")

# =====================================================
# PDF TEXT EXTRACTION (NO OCR)
# =====================================================

def extract_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")

        pages.append({
            "page": page_num + 1,
            "raw_text": text.splitlines()
        })

    return pages

# =====================================================
# DOC SUBTYPE LOGIC (FROM YOUR LAMBDA)
# =====================================================

def doc_subtype(raw_text, doc_subtype_keyword):
    for i in doc_subtype_keyword:
        for j in doc_subtype_keyword[i]:
            if re.search(j, " ".join(raw_text), re.IGNORECASE):
                return i.strip("d_")
    return "unknown"

# =====================================================
# MOCK WRAPPERS (REPLACE LATER)
# =====================================================

def mock_invoice_wrapper(raw_text):
    return [
        "INV-123",
        "Importer Name",
        "USD",
        ["HTS123"],
        ["100"],
        ["DESCRIPTION"],
        ["US"],
        ["10"],
        ["PCS"],
        "TOTAL",
        ["PART-001"]
    ]

def mock_7501_wrapper(raw_text):
    return [
        "ENTRY123",
        "AWB123",
        "BROKER NAME",
        ["HTS123"],
        ["100"],
        ["5"],
        ["1"]
    ]

# =====================================================
# JSON FORMAT (SIMPLIFIED IMPORT)
# =====================================================

def json_format_import(result):
    output = {
        "Entry Number": "",
        "AWB Number": "",
        "Broker Name": "",
        "LineItems": {
            "LineItemDetails": []
        }
    }

    for k, v in result.items():
        if k.endswith("7501"):
            output["Entry Number"] = v[0]
            output["AWB Number"] = v[1]
            output["Broker Name"] = v[2]

        if k.endswith("invoice"):
            for i in range(len(v[3])):
                output["LineItems"]["LineItemDetails"].append({
                    "HTS": v[3][i],
                    "Value": v[4][i],
                    "Description": v[5][i]
                })

    return output

# =====================================================
# MAIN PROCESSOR
# =====================================================

def process_pages(pages, document_type):
    doc_subtype_keyword = {
        "d_7501": [
            "OMB APPROVAL",
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
        subtype = doc_subtype(p["raw_text"], doc_subtype_keyword)

        if subtype == "invoice":
            result[f"page_{p['page']}_invoice"] = mock_invoice_wrapper(p["raw_text"])

        elif subtype == "7501":
            result[f"page_{p['page']}_7501"] = mock_7501_wrapper(p["raw_text"])

    if document_type == "import":
        return json_format_import(result)

    return result

# =====================================================
# UI
# =====================================================

doc_type = st.selectbox("Document Type", ["import", "export", "recon", "drawback"])
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    with st.spinner("Extracting text from PDF..."):
        pages = extract_pdf_text(uploaded_file)

    st.success(f"Processed {len(pages)} pages")

    with st.spinner("Running extraction logic..."):
        output = process_pages(pages, doc_type)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Extracted JSON")
        st.json(output)

    with col2:
        st.subheader("📝 Extracted Text")
        for p in pages:
            with st.expander(f"Page {p['page']}"):
                st.text("\n".join(p["raw_text"]))
