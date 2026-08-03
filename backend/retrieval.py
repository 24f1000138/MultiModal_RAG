import faiss
import numpy as np

from sentence_transformers import SentenceTransformer, CrossEncoder
from models import (Chunk,SessionLocal)

FAISS_INDEX_PATH = "rag2_faiss_index.bin"
MAPPING_PATH = "rag2_chunk_mapping.npy"

import os
import time

embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
session = SessionLocal()

if (os.path.exists(FAISS_INDEX_PATH) and os.path.exists(MAPPING_PATH)):
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
    chunk_id_mapping = np.load(MAPPING_PATH,allow_pickle=True).tolist()
    chunk_id_to_position = {chunk_id: position for position, chunk_id in enumerate(chunk_id_mapping)}

else:
    faiss_index = None
    chunk_id_mapping = []
    chunk_id_to_position = {}

def extract_rows(table_content):
    rows = []
    for line in table_content.split("\n"):
        line = line.strip()
        if line:
            rows.append(line)

    return rows

def rank_table_rows(query, rows):
    start = time.time()
    query_embedding = (embedding_model.encode(query))
    query_embedding = (query_embedding / np.linalg.norm(query_embedding))
    best_row = None
    best_score = -1

    for row in rows:
        row_embedding = (embedding_model.encode(row))
        row_embedding = (row_embedding / np.linalg.norm(row_embedding))
        score = np.dot(query_embedding,row_embedding)
        if score > best_score:
            best_score = score
            best_row = row
    print(
    "Table ranking:",
    time.time() - start
    )
    return best_row

def rerank_chunks(query, retrieved_chunks, final_k=5):
    if not retrieved_chunks:
        return []

    pairs = []
    for item in retrieved_chunks:
        content = f"""
            SECTION:
            {item["chunk"].metadata_json.get("section","")}

            {item["retrieved_content"]}
        """
        pairs.append([query, content])

    start = time.time()
    rerank_scores = reranker.predict(pairs)
    print(
    "Reranker:",
    time.time() - start
    )
    ranked_chunks = sorted(zip(retrieved_chunks, rerank_scores),key=lambda x: x[1],reverse=True)
    return [item for item, score in ranked_chunks[:final_k]]

def search_documents(keyword):
    docs = (session.query(Chunk.source_file).distinct().filter(Chunk.source_file.ilike(f"%{keyword}%")).all())
    return [doc[0] for doc in docs]

def retrieve_all_documents(query, candidate_k=20, top_k=5):
    if faiss_index is None:
        return []
    
    query_embedding = embedding_model.encode(f"Represent this sentence for searching relevant passages: {query}")
    query_vector = np.array([query_embedding]).astype("float32")
    start = time.time()
    distances, indices = faiss_index.search(query_vector,candidate_k)
    print("FAISS:", time.time() - start)
    retrieved_chunks = []

    for index_position in indices[0]:
        chunk_id = chunk_id_mapping[index_position]
        start = time.time()
        chunk = (session.query(Chunk).filter(Chunk.chunk_id == chunk_id).first())
        print("DB:", time.time() - start)
        if chunk:
            retrieved_content = chunk.content
            if chunk.chunk_type == "TableItem":
                rows = extract_rows(chunk.content)
                best_row = rank_table_rows(query,rows)
                retrieved_content = best_row

            retrieved_chunks.append({
                    "chunk": chunk,
                    "retrieved_content": retrieved_content
                })

    return rerank_chunks(query,retrieved_chunks,top_k)


def retrieve_document(query, source_files, candidate_k=20, top_k=5):
    s=0
    if faiss_index is None:
        return []
    
    candidate_chunks = (session.query(Chunk).filter(Chunk.source_file.in_(source_files)).all())
    if not candidate_chunks:
        return []

    candidate_positions = []
    for chunk in candidate_chunks:
        position = chunk_id_to_position.get(chunk.chunk_id)
        if position is not None:
            candidate_positions.append(position)

    if not candidate_positions:
        return []
    start = time.time()
    candidate_vectors = (faiss_index.reconstruct_batch(candidate_positions))
    p = time.time() - start
    print("FAISS Reconstruction:", p)
    s+=p

    start = time.time()
    query_embedding = embedding_model.encode(f"Represent this sentence for searching relevant passages: {query}")
    query_embedding = (query_embedding / np.linalg.norm(query_embedding))
    norms = np.linalg.norm(candidate_vectors,axis=1,keepdims=True)
    norms[norms == 0] = 1
    candidate_vectors = (candidate_vectors / norms)
    scores = np.dot(candidate_vectors,query_embedding)
    top_indices = np.argsort(scores)[::-1][:candidate_k]
    p = time.time() - start
    print("Cosine Similarity:", p)
    s+=p
    retrieved_chunks = []

    for idx in top_indices:
        position = candidate_positions[idx]
        chunk_id = chunk_id_mapping[position]
        start = time.time()
        chunk = (session.query(Chunk).filter(Chunk.chunk_id == chunk_id).first())
        p = time.time() - start
        print("DB:", p)
        s+=p
        if chunk:
            retrieved_content = chunk.content
            if chunk.chunk_type == "TableItem":
                rows = extract_rows(chunk.content)
                best_row = rank_table_rows(query,rows)
                table_title = (chunk.metadata_json.get("title","") if chunk.metadata_json else "")

                retrieved_content = (
                    f"TABLE TITLE: {table_title}\n\n"
                    f"{best_row}"
                )

            retrieved_chunks.append({
                    "chunk": chunk,
                    "retrieved_content": retrieved_content
                })
    print("Total Time:", s)
    return rerank_chunks(query,retrieved_chunks,top_k)