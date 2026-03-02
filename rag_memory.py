"""
soul.py — RAG Memory
Supports multiple backends: qdrant (default), chromadb, bm25 (fallback)
Supports multiple embedding providers: azure, openai, bm25
Pure REST for Qdrant/OpenAI — no native builds required.
"""

import os, re, math, time, hashlib
from pathlib import Path
from datetime import datetime


# ── BM25 fallback (zero deps) ─────────────────────────────────────────────────

class BM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1; self.b = b
        self.docs = []; self.tokenized = []

    def _tok(self, text):
        return re.findall(r'\w+', text.lower())

    def add(self, text):
        self.docs.append(text)
        self.tokenized.append(self._tok(text))

    def query(self, q, k=5):
        if not self.docs: return []
        qtoks = set(self._tok(q))
        N = len(self.docs)
        avgdl = sum(len(d) for d in self.tokenized) / N
        scores = []
        for i, toks in enumerate(self.tokenized):
            tlen = len(toks)
            freq = {t: toks.count(t) for t in qtoks if t in toks}
            score = sum(
                math.log((N - sum(t in d for d in self.tokenized) + 0.5) /
                         (sum(t in d for d in self.tokenized) + 0.5) + 1) *
                (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * tlen / avgdl))
                for t, f in freq.items()
            ) if freq else 0
            scores.append((score, i))
        scores.sort(reverse=True)
        return [self.docs[i] for _, i in scores[:k] if scores[0][0] > 0]


# ── Embedding providers ───────────────────────────────────────────────────────

def _embed_azure(texts, endpoint, api_key, deployment="text-embedding-3-large", api_version="2023-05-15"):
    import requests
    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
    r = requests.post(url, headers={"api-key": api_key, "Content-Type": "application/json"},
                      json={"input": texts}, timeout=30)
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


def _embed_openai(texts, api_key, model="text-embedding-3-small"):
    """OpenAI embeddings via direct REST — no SDK needed."""
    import requests
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"input": texts, "model": model},
        timeout=30
    )
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


# ── Qdrant REST client ────────────────────────────────────────────────────────

class QdrantREST:
    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.headers = {"api-key": api_key, "Content-Type": "application/json"}

    def _req(self, method, path, **kwargs):
        import requests
        r = requests.request(method, f"{self.url}{path}",
                             headers=self.headers, timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()

    def ensure_collection(self, name, size):
        try:
            self._req("GET", f"/collections/{name}")
        except Exception:
            self._req("PUT", f"/collections/{name}",
                      json={"vectors": {"size": size, "distance": "Cosine"}})

    def upsert(self, collection, points):
        self._req("PUT", f"/collections/{collection}/points",
                  json={"points": points})

    def search(self, collection, vector, k):
        r = self._req("POST", f"/collections/{collection}/points/search",
                      json={"vector": vector, "limit": k, "with_payload": True})
        return r.get("result", [])

    def count(self, collection):
        try:
            r = self._req("POST", f"/collections/{collection}/points/count",
                          json={"exact": True})
            return r.get("result", {}).get("count", 0)
        except Exception:
            return 0


# ── ChromaDB backend ──────────────────────────────────────────────────────────

class ChromaBackend:
    """Local ChromaDB — pip install chromadb, zero-config."""

    def __init__(self, collection_name="soul_memory", persist_path=None):
        try:
            import chromadb
        except ImportError:
            raise ImportError("pip install chromadb")

        if persist_path:
            self._client = chromadb.PersistentClient(path=persist_path)
        else:
            self._client = chromadb.Client()

        self._col = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, text, doc_id=None):
        doc_id = doc_id or hashlib.md5(text.encode()).hexdigest()
        # ChromaDB handles embeddings internally with its default model
        self._col.add(documents=[text], ids=[doc_id])

    def query(self, text, k=5):
        if self._col.count() == 0:
            return []
        results = self._col.query(query_texts=[text], n_results=min(k, self._col.count()))
        return results["documents"][0] if results["documents"] else []

    def count(self):
        return self._col.count()


# ── RAGMemory — main class ────────────────────────────────────────────────────

class RAGMemory:
    """
    Retrieval-Augmented Memory for soul.py.

    Backends:
        "qdrant"   — Qdrant Cloud via REST (default when configured)
        "chromadb" — Local ChromaDB (zero-config, pip install chromadb)
        "bm25"     — Keyword search (zero deps, always available)

    Embedding providers:
        "azure"  — Azure OpenAI (text-embedding-3-large)
        "openai" — OpenAI direct (text-embedding-3-small)
        (ChromaDB and BM25 handle their own embeddings)
    """

    def __init__(
        self,
        memory_path="MEMORY.md",
        mode="bm25",                        # "qdrant" | "chromadb" | "bm25"
        collection_name="soul_memory",
        # Qdrant
        qdrant_url=None,
        qdrant_api_key=None,
        # Azure embeddings
        azure_embedding_endpoint=None,
        azure_embedding_key=None,
        azure_embedding_deployment="text-embedding-3-large",
        # OpenAI embeddings
        openai_api_key=None,
        openai_embedding_model="text-embedding-3-small",
        # ChromaDB
        chroma_persist_path=None,
        # General
        k=5,
    ):
        self.memory_path  = Path(memory_path)
        self.mode         = mode
        self.collection   = collection_name
        self.k            = k
        self._bm25        = BM25()
        self._indexed     = set()

        # Embedding provider detection
        self._embed_provider = None
        self._az_ep  = azure_embedding_endpoint  or os.environ.get("AZURE_EMBEDDING_ENDPOINT","")
        self._az_key = azure_embedding_key        or os.environ.get("AZURE_EMBEDDING_KEY","")
        self._az_dep = azure_embedding_deployment
        self._oai_key = openai_api_key            or os.environ.get("OPENAI_API_KEY","")
        self._oai_model = openai_embedding_model

        if self._az_ep and self._az_key:
            self._embed_provider = "azure"
            self._vec_size = 3072
        elif self._oai_key:
            self._embed_provider = "openai"
            self._vec_size = 1536  # text-embedding-3-small

        # Backend init
        if mode == "qdrant":
            url = qdrant_url or os.environ.get("QDRANT_URL","")
            key = qdrant_api_key or os.environ.get("QDRANT_API_KEY","")
            if not url: raise ValueError("QDRANT_URL required for qdrant mode")
            if not self._embed_provider: raise ValueError("Embedding provider required for qdrant mode (set AZURE or OPENAI keys)")
            self._qdrant = QdrantREST(url, key)
            self._qdrant.ensure_collection(collection_name, self._vec_size)
        elif mode == "chromadb":
            self._chroma = ChromaBackend(collection_name, chroma_persist_path)
        # bm25: no init needed

        # Index existing memory
        self._index_memory()

    def _embed(self, texts):
        if self._embed_provider == "azure":
            return _embed_azure(texts, self._az_ep, self._az_key, self._az_dep)
        elif self._embed_provider == "openai":
            return _embed_openai(texts, self._oai_key, self._oai_model)
        raise ValueError("No embedding provider configured")

    def _parse_entries(self):
        if not self.memory_path.exists(): return []
        text = self.memory_path.read_text()
        parts = re.split(r'\n(?=## )', text)
        return [p.strip() for p in parts if p.strip() and not p.strip().startswith("# MEMORY")]

    def _index_memory(self):
        entries = self._parse_entries()
        new = [e for e in entries if e not in self._indexed]
        if not new: return

        if self.mode == "qdrant" and new:
            vecs = self._embed(new)
            points = [{"id": abs(hash(e)) % (2**63),
                       "vector": v, "payload": {"text": e}}
                      for e, v in zip(new, vecs)]
            self._qdrant.upsert(self.collection, points)

        elif self.mode == "chromadb":
            for e in new:
                self._chroma.add(e)

        for e in new:
            self._bm25.add(e)
            self._indexed.add(e)

    def retrieve(self, query, k=None):
        k = k or self.k
        self._index_memory()

        if self.mode == "qdrant" and self._embed_provider:
            vec = self._embed([query])[0]
            results = self._qdrant.search(self.collection, vec, k)
            chunks = [r["payload"]["text"] for r in results]
        elif self.mode == "chromadb":
            chunks = self._chroma.query(query, k)
        else:
            chunks = self._bm25.query(query, k)

        if not chunks:
            return f"No relevant memories found for: '{query}'"
        return "## Relevant memories\n\n" + "\n\n---\n".join(chunks)

    def append(self, note):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## {ts}\n{note}"
        with open(self.memory_path, "a") as f:
            f.write(f"\n\n{entry}")
        # Index new entry immediately
        if self.mode == "qdrant" and self._embed_provider:
            vec = self._embed([entry])[0]
            self._qdrant.upsert(self.collection,
                [{"id": abs(hash(entry)) % (2**63),
                  "vector": vec, "payload": {"text": entry}}])
        elif self.mode == "chromadb":
            self._chroma.add(entry)
        self._bm25.add(entry)
        self._indexed.add(entry)

    def count(self):
        if self.mode == "qdrant":
            return self._qdrant.count(self.collection)
        elif self.mode == "chromadb":
            return self._chroma.count()
        return len(self._bm25.docs)
