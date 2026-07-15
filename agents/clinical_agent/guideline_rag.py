"""
LangChain RAG over curated IDSA/WHO/ICMR guideline corpus + published case studies.
Uses BM25 retrieval (no embedding API required — works on Cloud Run offline).
"""

import json
import os
from functools import lru_cache
from typing import Optional

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
_GUIDELINES_PATH = os.path.join(_DATA_DIR, "guidelines_corpus.json")
_CASE_STUDIES_PATH = os.path.join(_DATA_DIR, "published_case_studies.json")

_retriever: Optional[BM25Retriever] = None
_case_studies: Optional[list] = None


def _load_guidelines() -> list[dict]:
    with open(_GUIDELINES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_case_studies() -> list[dict]:
    with open(_CASE_STUDIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _build_documents() -> list[Document]:
    docs = []
    for g in _load_guidelines():
        meta = {
            "id": g["id"],
            "title": g["title"],
            "type": "guideline",
            "diagnosis_tags": g.get("diagnosis_tags", []),
            "pathogen_tags": g.get("pathogen_tags", []),
        }
        docs.append(Document(page_content=g["text"], metadata=meta))
    for cs in _load_case_studies():
        body = f"{cs['title']}. {cs['summary']} Clinical lesson: {cs['clinical_lesson']} Source: {cs['source']}"
        docs.append(Document(
            page_content=body,
            metadata={
                "id": cs["id"],
                "title": cs["title"],
                "type": "case_study",
                "tags": cs.get("tags", []),
                "source": cs.get("source", ""),
                "url": cs.get("url", ""),
            },
        ))
    return docs


@lru_cache(maxsize=1)
def get_bm25_retriever() -> BM25Retriever:
    global _retriever
    documents = _build_documents()
    _retriever = BM25Retriever.from_documents(documents, k=4)
    return _retriever


def retrieve_clinical_evidence(
    diagnosis: str,
    pathogen: str = "Unknown",
    query: Optional[str] = None,
    top_k: int = 3,
) -> dict:
    """
    LangChain BM25 RAG — retrieve guideline chunks + matching case studies.
    Called as clinical agent tool and shown in physician UI.
    """
    retriever = get_bm25_retriever()
    retriever.k = top_k + 2

    search_query = query or f"{diagnosis} {pathogen} antibiotic stewardship empiric therapy India"
    hits = retriever.invoke(search_query)

    # Re-rank: boost tag matches
    diag_lower = diagnosis.lower()
    path_lower = pathogen.lower()
    scored = []
    for doc in hits:
        score = 0
        tags = doc.metadata.get("diagnosis_tags", []) + doc.metadata.get("tags", [])
        for t in tags:
            tl = str(t).lower()
            if tl in diag_lower or diag_lower in tl:
                score += 2
            if tl in path_lower or path_lower in tl:
                score += 2
            if tl == "all":
                score += 1
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_docs = [d for _, d in scored[:top_k]]

    evidence = []
    for doc in top_docs:
        evidence.append({
            "id": doc.metadata.get("id"),
            "title": doc.metadata.get("title"),
            "type": doc.metadata.get("type", "guideline"),
            "excerpt": doc.page_content[:500] + ("…" if len(doc.page_content) > 500 else ""),
            "source": doc.metadata.get("source", "Curated guideline corpus"),
            "url": doc.metadata.get("url", ""),
        })

    # Matched case studies by tags
    studies = _load_case_studies()
    matched_studies = []
    for cs in studies:
        tags = [t.lower() for t in cs.get("tags", [])]
        if any(t in diag_lower or t in path_lower for t in tags):
            matched_studies.append({
                "id": cs["id"],
                "title": cs["title"],
                "summary": cs["summary"],
                "clinical_lesson": cs["clinical_lesson"],
                "source": cs["source"],
                "url": cs.get("url", ""),
            })
    if not matched_studies:
        matched_studies = [{
            "id": cs["id"],
            "title": cs["title"],
            "summary": cs["summary"],
            "clinical_lesson": cs["clinical_lesson"],
            "source": cs["source"],
            "url": cs.get("url", ""),
        } for cs in studies[:2]]

    return {
        "query": search_query,
        "retrieval_method": "LangChain BM25Retriever (guidelines + case studies)",
        "evidence_chunks": evidence,
        "related_case_studies": matched_studies[:3],
        "corpus_size": len(_build_documents()),
        "disclaimer": "Curated public guidelines and published surveillance summaries — not patient-specific medical advice.",
    }
