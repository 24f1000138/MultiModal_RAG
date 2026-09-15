from pathlib import Path
import shutil
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.ingestion import ingest_document
from backend.retrieval import (
    retrieve_document,
    retrieve_all_documents,
    search_documents,
)
from backend.llm import generate_answer
from backend.evaluator import evaluate_rag


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
evaluation_store: dict[str, dict[str, Any]] = {}

def resolve_project_path(path_value: str) -> Path:
    """
    Resolve a relative or absolute path and ensure that it remains
    inside PROJECT_ROOT.
    """

    normalized_path = path_value.replace("\\", "/")
    candidate = Path(normalized_path)

    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate

    resolved_path = candidate.resolve()

    try:
        resolved_path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Access to this path is not allowed.",
        )

    return resolved_path


@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    ocr_mode: str = Form("Auto Detect"),
):
    safe_filename = Path(file.filename).name
    pdf_path = UPLOAD_DIR / safe_filename

    with open(pdf_path, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    ingest_document(
        str(pdf_path),
        ocr_mode=ocr_mode,
    )

    return {
        "status": "ok",
        "path": str(pdf_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


@app.get("/search")
def search(q: str):
    return {
        "documents": search_documents(q),
    }

def run_evaluation(
    evaluation_id: str,
    question: str,
    retrieved_context: str,
    generated_answer: str,
):
    """
    Runs the evaluator after the answer has already been returned
    to the frontend.
    """

    try:
        evaluation = evaluate_rag(
            question=question,
            retrieved_context=retrieved_context,
            generated_answer=generated_answer,
        )

        evaluation_store[evaluation_id] = {
            "status": "completed",
            "evaluation": evaluation,
        }

    except Exception as error:
        evaluation_store[evaluation_id] = {
            "status": "failed",
            "error": str(error),
        }

@app.post("/retrieve")
async def retrieve(
    body: dict,
    background_tasks: BackgroundTasks,
):
    query = body["query"]
    mode = body.get("mode", "all")
    documents = body.get("documents", [])

    if mode == "specific":
        chunks = retrieve_document(query, documents)
    else:
        chunks = retrieve_all_documents(query)

    contexts = []

    for item in chunks:
        chunk = item["chunk"]
        content = item["retrieved_content"]
        metadata = chunk.metadata_json or {}

        contexts.append(
            f"""
SOURCE FILE: {chunk.source_file}
PAGE NUMBER: {chunk.page_number}
SECTION: {metadata.get("section", "")}
CHUNK TYPE: {chunk.chunk_type}
CHUNK ID: {chunk.chunk_id}

CONTENT:
{content}
""".strip()
        )

    context_text = "\n\n".join(contexts)

    # Generate the answer first
    answer = generate_answer(
        query,
        context_text,
    )

    # Create an ID for this evaluation task
    evaluation_id = str(uuid4())

    # Store the initial evaluation status
    evaluation_store[evaluation_id] = {
        "status": "pending",
    }

    # Start evaluation in the background
    background_tasks.add_task(
        run_evaluation,
        evaluation_id,
        query,
        context_text,
        answer,
    )

    # Return immediately after answer generation
    return {
        "answer": answer,
        "evaluation_id": evaluation_id,
        "evaluation_status": "pending",
        "chunks": [
            {
                "chunk": {
                    "chunk_id": item["chunk"].chunk_id,
                    "source_file": item["chunk"].source_file,
                    "page_number": item["chunk"].page_number,
                    "chunk_type": item["chunk"].chunk_type,
                    "image_path": item["chunk"].image_path,
                    "metadata_json": item["chunk"].metadata_json,
                },
                "retrieved_content": item["retrieved_content"],
            }
            for item in chunks
        ],
    }

@app.get("/evaluation/{evaluation_id}")
def get_evaluation(evaluation_id: str):
    result = evaluation_store.get(evaluation_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found.",
        )

    return result

@app.get("/image")
def get_image(path: str):
    image_path = resolve_project_path(path)

    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Image not found.",
        )

    if image_path.suffix.lower() not in {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format.",
        )

    return FileResponse(str(image_path))


@app.get("/pdf")
def get_pdf(path: str):
    pdf_path = resolve_project_path(path)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF not found: {pdf_path}",
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )