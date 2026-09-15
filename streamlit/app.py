import streamlit as st
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
from backend.ingestion import ingest_document
from backend.retrieval import (retrieve_document,retrieve_all_documents, search_documents, load_vector_store)
from backend.llm import generate_answer
from streamlit_pdf_viewer import pdf_viewer

st.set_page_config(page_title="Multimodal RAG",page_icon="📚",layout="wide")
st.title("Multimodal RAG System")
st.sidebar.header("Document Management")
uploaded_file = st.sidebar.file_uploader("Upload PDF",type=["pdf"])

if uploaded_file:
    os.makedirs("uploads", exist_ok=True)
    save_path = os.path.join("uploads",uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    ocr_mode = st.sidebar.radio(
        "OCR Mode",
        [
            "Auto Detect",
            "Force OCR",
            "Disable OCR"
        ]
    )

    if st.sidebar.button("Ingest Document"):
        with st.spinner("Ingesting..."):
            ingest_document(save_path, ocr_mode=ocr_mode)
        load_vector_store()
        st.sidebar.success("Ingestion Complete")

st.header("Search")
search_mode = st.radio("Search Mode",["Specific Document","All Documents"])
selected_documents = []
if search_mode == "Specific Document":
    document_keyword = st.text_input("Search Document")
    matching_documents = []
    if document_keyword:
        matching_documents = search_documents(document_keyword)
        if matching_documents:
            selected_documents = st.multiselect("Matching Documents",matching_documents)

        else:
            st.warning("No matching documents found.")

query = st.text_input("Ask a Question")

if st.button("Ask"):
    if not query:
        st.warning("Please enter a question.")

    else:
        with st.spinner("Retrieving relevant information..."):
            if search_mode == "Specific Document":
                if not selected_documents:
                    st.warning("Please select a document.")
                    st.stop()

                retrieved_chunks = retrieve_document(query,selected_documents)

            else:
                retrieved_chunks = retrieve_all_documents(query)

            contexts = []
            for item in retrieved_chunks:
                chunk = item["chunk"]
                content = item["retrieved_content"]
                contexts.append(f"""
                    SOURCE FILE: {chunk.source_file}
                    PAGE NUMBER: {chunk.page_number}
                    SECTION: {chunk.metadata_json.get("section","")}
                    CHUNK TYPE: {chunk.chunk_type}

                    CONTENT:
                    {content}""")

            context_text = "\n\n".join(contexts)
            answer = generate_answer(query,context_text)
            st.session_state.answer = answer
            st.session_state.retrieved_chunks = retrieved_chunks

if "answer" in st.session_state:
    answer = st.session_state.answer
    retrieved_chunks = st.session_state.retrieved_chunks
    st.subheader("Answer")
    st.write(answer)
    st.subheader("Sources")
    shown = set()

    for item in retrieved_chunks:
        chunk = item["chunk"]
        source = (
            f"{os.path.basename(chunk.source_file)} "
            f"(Page {chunk.page_number})"
        )

        if source not in shown:
            st.markdown(f"- {source}")
            shown.add(source)

    with st.expander("Retrieved Context"):
        for i, item in enumerate(retrieved_chunks, start=1):
            chunk = item["chunk"]
            content = item["retrieved_content"]
                
            if st.button(f"Open Page {chunk.page_number}",key=f"open_{i}"):
                st.session_state.pdf_path = chunk.source_file
                st.session_state.page_no = chunk.page_number
                print("PDF PATH:", chunk.source_file)
                print("PAGE NO:", chunk.page_number)
            
            st.markdown(f"""
                ### Chunk {i}
                **Source:** {os.path.basename(chunk.source_file)}
                **Section:** {chunk.metadata_json.get("section","N/A")}
                **Page:** {chunk.page_number}
                **Type:** {chunk.chunk_type}
                **Content:** {content}""")
                
            if chunk.image_path and os.path.exists(chunk.image_path):
                st.image(chunk.image_path,caption=f"Page {chunk.page_number}")

    if "pdf_path" in st.session_state and os.path.exists(st.session_state.pdf_path):
        print("\n========== PDF VIEWER ==========")
        print("PDF PATH:", st.session_state.pdf_path)
        print("EXISTS:", os.path.exists(st.session_state.pdf_path))
        print("PAGE:", st.session_state.page_no)
        st.subheader(f"PDF Viewer - Page {st.session_state.page_no}")  
        with open(st.session_state.pdf_path, "rb") as f:
            pdf_bytes = f.read()

        pdf_viewer(pdf_bytes,pages_to_render=[st.session_state.page_no])

