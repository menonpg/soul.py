"""
soul.py v2.0 — HybridAgent (RAG + RLM)
Pure REST — no native deps, works on any platform.
Calls Anthropic API directly via requests.
"""
import os, sys, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rag_memory import RAGMemory, BM25
from rlm_memory import RLMMemory
from router import classify


# ── Minimal Anthropic REST client ─────────────────────────────────────────────

class AnthropicREST:
    """Calls Anthropic API via requests. No SDK needed."""
    BASE = "https://api.anthropic.com/v1"

    def __init__(self, api_key):
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def messages_create(self, model, max_tokens, messages, system=None):
        payload = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            payload["system"] = system
        r = requests.post(f"{self.BASE}/messages", headers=self.headers,
                          json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()


# ── HybridAgent ───────────────────────────────────────────────────────────────

class HybridAgent:
    """
    soul.py v2.0 — RAG + RLM hybrid with automatic query routing.

    Args:
        soul_path: Path to SOUL.md
        memory_path: Path to MEMORY.md
        mode: "auto" | "rag" | "rlm"
        anthropic_key: Anthropic API key (or ANTHROPIC_API_KEY env var)
        qdrant_url, qdrant_api_key: Qdrant credentials (optional, falls back to bm25)
        azure_embedding_endpoint, azure_embedding_key: Azure embeddings (for qdrant mode)
        k: RAG retrieval count
        rlm_chunk_size: Entries per RLM recursive sub-call
    """

    DEFAULT_SOUL = (
        "You are a helpful, persistent AI assistant with memory. "
        "Be concise and direct. Acknowledge what you remember naturally."
    )

    def __init__(
        self,
        soul_path="SOUL.md",
        memory_path="MEMORY.md",
        mode="auto",
        anthropic_key=None,
        qdrant_url=None,
        qdrant_api_key=None,
        azure_embedding_endpoint=None,
        azure_embedding_key=None,
        collection_name="soul_v2_memory",
        k=5,
        rlm_chunk_size=10,
        chat_model="claude-haiku-4-5",
        router_model="claude-haiku-4-5",
    ):
        self.soul_path   = Path(soul_path)
        self.memory_path = Path(memory_path)
        self.mode = mode
        self.chat_model   = chat_model
        self.router_model = router_model
        self._history = []

        # Ensure files exist
        if not self.soul_path.exists():
            self.soul_path.write_text(self.DEFAULT_SOUL)
        if not self.memory_path.exists():
            self.memory_path.write_text("# MEMORY.md\n")

        # Anthropic client
        key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY","")
        if not key: raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = AnthropicREST(key)

        # RAG memory
        qd_url = qdrant_url or os.environ.get("QDRANT_URL","")
        az_ep  = azure_embedding_endpoint or os.environ.get("AZURE_EMBEDDING_ENDPOINT","")
        self._rag = RAGMemory(
            memory_path=str(self.memory_path),
            mode="qdrant" if (qd_url and az_ep) else "bm25",
            collection_name=collection_name,
            qdrant_url=qd_url,
            qdrant_api_key=qdrant_api_key or os.environ.get("QDRANT_API_KEY",""),
            azure_embedding_endpoint=az_ep,
            azure_embedding_key=azure_embedding_key or os.environ.get("AZURE_EMBEDDING_KEY",""),
            k=k,
        )

        # RLM memory
        self._rlm = RLMMemory(
            memory_path=str(self.memory_path),
            chunk_size=rlm_chunk_size,
        )

    def _read_soul(self):
        return self.soul_path.read_text().strip()

    def ask(self, question: str, remember: bool = True) -> dict:
        """
        Ask the agent. Returns a rich result dict.

        Returns:
            answer, route, router_ms, retrieval_ms, total_ms,
            rag_context (if RAG), rlm_meta (if RLM)
        """
        t0 = time.time()
        router_ms = 0

        # Route
        if self.mode == "auto":
            classification = classify(question, self._client, model=self.router_model)
            route = classification["route"]
            router_ms = classification["latency_ms"]
        else:
            route = "EXHAUSTIVE" if self.mode == "rlm" else "FOCUSED"

        if route == "FOCUSED":
            # RAG path
            t1 = time.time()
            rag_context = self._rag.retrieve(question)
            retrieval_ms = int((time.time()-t1)*1000)

            system = f"{self._read_soul()}\n\n---\n\n{rag_context}"
            self._history.append({"role":"user","content":question})
            answer = self._client.messages_create(
                model=self.chat_model, max_tokens=512,
                messages=self._history, system=system,
            )
            self._history.append({"role":"assistant","content":answer})

            if remember:
                self._rag.append(f"Q: {question}\nA: {answer}")

            return {
                "answer": answer, "route": "RAG",
                "router_ms": router_ms, "retrieval_ms": retrieval_ms,
                "total_ms": int((time.time()-t0)*1000),
                "rag_context": rag_context, "rlm_meta": None,
            }

        else:
            # RLM path
            t1 = time.time()
            rlm_result = self._rlm.retrieve(question, self._client)
            retrieval_ms = int((time.time()-t1)*1000)
            answer = rlm_result["answer"]

            if remember:
                self._rag.append(f"Q: {question}\nA: {answer}")

            return {
                "answer": answer, "route": "RLM",
                "router_ms": router_ms, "retrieval_ms": retrieval_ms,
                "total_ms": int((time.time()-t0)*1000),
                "rag_context": None,
                "rlm_meta": {
                    "chunks_processed": rlm_result["chunks_processed"],
                    "relevant_chunks": rlm_result["relevant_chunks"],
                    "sub_summaries": rlm_result["sub_summaries"],
                },
            }

    def remember(self, note: str):
        self._rag.append(note)

    def reset_conversation(self):
        self._history = []
