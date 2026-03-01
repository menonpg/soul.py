"""
soul.py v1.0 — RAG Memory Backend
Two modes:
  "qdrant" — Azure text-embedding-3-large + Qdrant Cloud REST API (semantic)
  "bm25"   — Pure Python keyword retrieval (zero deps, offline fallback)

No native builds required — pure Python + requests only.
"""

import os, re, math, json, uuid, requests
from pathlib import Path
from datetime import datetime
from collections import Counter


# ── BM25 (pure Python, zero deps) ────────────────────────────────────────────

class BM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1; self.b = b
        self.docs = []; self.tf = []
        self.df = Counter(); self.avgdl = 0

    def _tok(self, text):
        return re.findall(r'\w+', text.lower())

    def add(self, doc):
        tokens = self._tok(doc)
        self.docs.append(doc)
        tf = Counter(tokens)
        self.tf.append(tf)
        for t in set(tokens): self.df[t] += 1
        n = len(self.docs)
        self.avgdl = (self.avgdl * (n-1) + len(tokens)) / n

    def score(self, query, idx):
        N = len(self.docs)
        dl = sum(self.tf[idx].values())
        score = 0.0
        for t in self._tok(query):
            if t not in self.tf[idx]: continue
            idf = math.log((N - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
            tf = self.tf[idx][t]
            score += idf * tf * (self.k1+1) / (tf + self.k1*(1-self.b+self.b*dl/max(self.avgdl,1)))
        return score

    def retrieve(self, query, k=5):
        if not self.docs: return []
        scores = sorted([(self.score(query, i), i) for i in range(len(self.docs))], reverse=True)
        return [self.docs[i] for _, i in scores[:k]]


# ── Azure Embeddings (pure REST) ──────────────────────────────────────────────

def azure_embed(text, endpoint, api_key,
                deployment="text-embedding-3-large", api_version="2023-05-15"):
    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
    r = requests.post(url,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={"input": text[:8000]}, timeout=15)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


# ── Qdrant REST client (no grpc, no native deps) ──────────────────────────────

class QdrantREST:
    """Minimal Qdrant Cloud client over REST. No qdrant-client package needed."""

    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.headers = {"api-key": api_key, "Content-Type": "application/json"}

    def _req(self, method, path, **kwargs):
        r = requests.request(method, f"{self.url}{path}",
                             headers=self.headers, timeout=20, **kwargs)
        r.raise_for_status()
        return r.json()

    def collection_exists(self, name):
        try:
            self._req("GET", f"/collections/{name}")
            return True
        except: return False

    def create_collection(self, name, vector_size=3072):
        self._req("PUT", f"/collections/{name}", json={
            "vectors": {"size": vector_size, "distance": "Cosine"}
        })

    def count(self, name):
        r = self._req("POST", f"/collections/{name}/points/count", json={"exact": True})
        return r["result"]["count"]

    def upsert(self, name, point_id, vector, payload):
        self._req("PUT", f"/collections/{name}/points", json={
            "points": [{"id": point_id, "vector": vector, "payload": payload}]
        })

    def search(self, name, vector, k=5):
        r = self._req("POST", f"/collections/{name}/points/search", json={
            "vector": vector, "limit": k, "with_payload": True
        })
        return r["result"]


# ── Main RAGMemory ────────────────────────────────────────────────────────────

class RAGMemory:
    """
    Pluggable RAG memory for soul.py.

    Args:
        memory_path: Path to MEMORY.md
        mode: "qdrant" (semantic) or "bm25" (keyword, zero deps)
        collection_name: Qdrant collection (only for qdrant mode)
        qdrant_url, qdrant_api_key: Qdrant Cloud credentials
        azure_embedding_endpoint, azure_embedding_key: Azure OpenAI credentials
        azure_embedding_deployment: Default "text-embedding-3-large"
        k: Results to retrieve per query
    """

    def __init__(self, memory_path="MEMORY.md", mode="qdrant",
                 collection_name="soul_memory",
                 qdrant_url=None, qdrant_api_key=None,
                 azure_embedding_endpoint=None, azure_embedding_key=None,
                 azure_embedding_deployment="text-embedding-3-large",
                 azure_embedding_api_version="2023-05-15",
                 k=5):

        self.memory_path = Path(memory_path)
        self.mode = mode
        self.k = k
        self.collection_name = collection_name
        self._az_ep      = azure_embedding_endpoint or os.environ.get("AZURE_EMBEDDING_ENDPOINT","")
        self._az_key     = azure_embedding_key      or os.environ.get("AZURE_EMBEDDING_KEY","")
        self._az_deploy  = azure_embedding_deployment
        self._az_version = azure_embedding_api_version

        if mode == "qdrant":
            url = qdrant_url or os.environ.get("QDRANT_URL","")
            key = qdrant_api_key or os.environ.get("QDRANT_API_KEY","")
            self._qd = QdrantREST(url, key)
            if not self._qd.collection_exists(collection_name):
                self._qd.create_collection(collection_name, vector_size=3072)
            self._next_id = self._qd.count(collection_name)
        else:
            self._bm25 = BM25()
            self._indexed = 0

        if self.memory_path.exists():
            self._index_existing()

    def _parse_entries(self):
        text = self.memory_path.read_text()
        return [b.strip() for b in re.split(r'\n## ', text)[1:] if b.strip()]

    def _index_existing(self):
        entries = self._parse_entries()
        if self.mode == "qdrant":
            new = entries[self._next_id:]
            for e in new: self._add_qdrant(e)
        else:
            for e in entries[self._indexed:]:
                self._bm25.add(e)
            self._indexed = len(entries)

    def _add_qdrant(self, text):
        vec = azure_embed(text, self._az_ep, self._az_key, self._az_deploy, self._az_version)
        self._qd.upsert(self.collection_name, self._next_id, vec, {"text": text})
        self._next_id += 1

    def append(self, exchange):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"{ts}\n{exchange.strip()}"
        with open(self.memory_path, "a") as f:
            f.write(f"\n## {entry}\n")
        if self.mode == "qdrant":
            self._add_qdrant(entry)
        else:
            self._bm25.add(entry)
            self._indexed += 1

    def retrieve(self, query, k=None):
        k = k or self.k
        if self.mode == "qdrant":
            total = self._qd.count(self.collection_name)
            if total == 0: return "# Your Memory\n(No memories yet.)\n"
            vec = azure_embed(query, self._az_ep, self._az_key, self._az_deploy, self._az_version)
            results = self._qd.search(self.collection_name, vec, k=min(k, total))
            docs = [r["payload"]["text"] for r in results]
        else:
            docs = self._bm25.retrieve(query, k)
            total = self._indexed

        if not docs: return "# Your Memory\n(Nothing relevant found.)\n"
        return f"# Relevant Memories ({len(docs)} of {total} retrieved)\n\n" + "\n\n---\n".join(docs)

    def count(self):
        return self._qd.count(self.collection_name) if self.mode == "qdrant" else self._indexed
