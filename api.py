from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os, shutil

from ingestion import ingest_document
from retrieval import retrieve_document, retrieve_all_documents, search_documents
from llm import generate_answer

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/ingest")
async def ingest(file: UploadFile = File(...), ocr_mode: str = Form("Auto Detect")):
    os.makedirs("uploads", exist_ok=True)
    path = f"uploads/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    ingest_document(path, ocr_mode=ocr_mode)
    return {"status": "ok"}

@app.get("/search")
def search(q: str):
    return {"documents": search_documents(q)}

@app.post("/retrieve")
async def retrieve(body: dict):
    query = body["query"]
    mode  = body.get("mode", "all")
    docs  = body.get("documents", [])

    chunks = retrieve_document(query, docs) if mode == "specific" else retrieve_all_documents(query)

    contexts = []
    for item in chunks:
        chunk = item["chunk"]
        content = item["retrieved_content"]
        contexts.append(f"""
            SOURCE FILE: {chunk.source_file}
            PAGE NUMBER: {chunk.page_number}
            SECTION: {chunk.metadata_json.get("section","")}
            CHUNK TYPE: {chunk.chunk_type}
            CONTENT: {content}""")

    answer = generate_answer(query, "\n\n".join(contexts))
    return {
        "answer": answer,
        "chunks": [
            {
                "chunk": {
                    "source_file": item["chunk"].source_file,
                    "page_number": item["chunk"].page_number,
                    "chunk_type": item["chunk"].chunk_type,
                    "image_path": item["chunk"].image_path,
                    "metadata_json": item["chunk"].metadata_json,
                },
                "retrieved_content": item["retrieved_content"]
            }
            for item in chunks
        ]
    }

@app.get("/image")
def get_image(path: str):
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "not found"}

@app.get("/pdf")
def get_pdf(path: str):
    if os.path.exists(path):
        return FileResponse(path, media_type="application/pdf")
    return {"error": "not found"}