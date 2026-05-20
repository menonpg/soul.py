"""
soul.py v2.0 — HybridAgent (RAG + RLM)
Pure REST — no native deps, works on any platform.
Supports Anthropic, Gemini, and OpenAI-compatible APIs.
"""
import os, sys, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rag_memory import RAGMemory, BM25
from rlm_memory import RLMMemory
from graph_memory import GraphMemory, RLMGraphMemory
from router import classify


# ── Minimal REST clients ──────────────────────────────────────────────────────

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


class GeminiREST:
    """Calls Google Gemini API via requests. No SDK needed."""
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key):
        self.api_key = api_key

    def messages_create(self, model, max_tokens, messages, system=None):
        # Convert Anthropic-style messages to Gemini format
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens}
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        
        url = f"{self.BASE}/models/{model}:generateContent?key={self.api_key}"
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


class OpenAICompatibleREST:
    """Calls OpenAI-compatible APIs (OpenAI, Ollama, LM Studio, etc.)"""
    
    def __init__(self, api_key, base_url="https://api.openai.com/v1"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
        }

    def messages_create(self, model, max_tokens, messages, system=None):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        
        payload = {"model": model, "max_tokens": max_tokens, "messages": msgs}
        r = requests.post(f"{self.base_url}/chat/completions", 
                          headers=self.headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


# ── Provider defaults ─────────────────────────────────────────────────────────

PROVIDER_DEFAULTS = {
    "anthropic": {
        "chat_model": "claude-haiku-4-5",
        "router_model": "claude-haiku-4-5",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "chat_model": "gemini-2.0-flash",
        "router_model": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "openai": {
        "chat_model": "gpt-4o-mini",
        "router_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "openai-compatible": {
        "chat_model": "llama3.2",
        "router_model": "llama3.2",
        "env_key": "OPENAI_API_KEY",
    },
}


# ── HybridAgent ───────────────────────────────────────────────────────────────

class HybridAgent:
    """
    soul.py v2.0 — RAG + RLM hybrid with automatic query routing.

    Args:
        soul_path: Path to SOUL.md
        memory_path: Path to MEMORY.md
        mode: "auto" | "rag" | "rlm" | "graph" | "graph-regex" | "rlm-graph" | "rlm-graph-regex"
        provider: "anthropic" | "gemini" | "openai" | "openai-compatible"
        api_key: API key for the provider (or use env var)
        base_url: For openai-compatible, the base URL (e.g., http://localhost:11434/v1)
        chat_model: Model for main chat (defaults per provider)
        router_model: Model for query routing (defaults per provider)
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
        provider="anthropic",
        api_key=None,
        base_url=None,
        qdrant_url=None,
        qdrant_api_key=None,
        azure_embedding_endpoint=None,
        azure_embedding_key=None,
        collection_name="soul_v2_memory",
        k=5,
        rlm_chunk_size=10,
        chat_model=None,
        router_model=None,
        # Legacy params for backwards compatibility
        anthropic_key=None,
        gemini_key=None,
        openai_key=None,
    ):
        self.soul_path   = Path(soul_path)
        self.memory_path = Path(memory_path)
        self.mode = mode
        self.provider = provider.lower()
        self._history = []

        # Get provider defaults
        if self.provider not in PROVIDER_DEFAULTS:
            raise ValueError(f"Unknown provider: {self.provider}. "
                           f"Supported: {list(PROVIDER_DEFAULTS.keys())}")
        
        defaults = PROVIDER_DEFAULTS[self.provider]
        self.chat_model = chat_model or defaults["chat_model"]
        self.router_model = router_model or defaults["router_model"]

        # Resolve API key (check explicit params, then legacy params, then env)
        key = api_key
        if not key and self.provider == "anthropic":
            key = anthropic_key
        if not key and self.provider == "gemini":
            key = gemini_key
        if not key and self.provider in ("openai", "openai-compatible"):
            key = openai_key
        if not key:
            key = os.environ.get(defaults["env_key"], "")
        
        if not key and self.provider != "openai-compatible":
            raise ValueError(f"{defaults['env_key']} not set")

        # Create client
        if self.provider == "anthropic":
            self._client = AnthropicREST(key)
        elif self.provider == "gemini":
            self._client = GeminiREST(key)
        elif self.provider == "openai":
            self._client = OpenAICompatibleREST(key)
        elif self.provider == "openai-compatible":
            url = base_url or os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
            self._client = OpenAICompatibleREST(key, base_url=url)

        # Ensure files exist
        if not self.soul_path.exists():
            self.soul_path.write_text(self.DEFAULT_SOUL)
        if not self.memory_path.exists():
            self.memory_path.write_text("# MEMORY.md\n")

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

        # Graph memory (regex-based, no LLM cost)
        graph_mode = "regex"  # default
        if self.mode in ("graph", "rlm-graph"):
            graph_mode = "llm"
        elif self.mode in ("graph-regex", "rlm-graph-regex"):
            graph_mode = "regex"

        if self.mode in ("graph", "graph-regex", "rlm-graph", "rlm-graph-regex"):
            if self.mode in ("rlm-graph", "rlm-graph-regex"):
                self._rlm_graph = RLMGraphMemory(
                    memory_path=str(self.memory_path),
                    mode=graph_mode,
                    chunk_size=rlm_chunk_size,
                )
            else:
                self._graph = GraphMemory(
                    memory_path=str(self.memory_path),
                    mode=graph_mode,
                    llm_client=self._client if graph_mode == "llm" else None,
                    llm_model=self.router_model,
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
        elif self.mode in ("graph", "graph-regex"):
            route = "GRAPH"
        elif self.mode in ("rlm-graph", "rlm-graph-regex"):
            route = "RLM_GRAPH"
        else:
            route = "EXHAUSTIVE" if self.mode == "rlm" else "FOCUSED"

        if route == "GRAPH":
            # Graph-only path
            t1 = time.time()
            graph_context = self._graph.retrieve(question)
            retrieval_ms = int((time.time()-t1)*1000)

            system = f"{self._read_soul()}\n\n---\n\n{graph_context}"
            self._history.append({"role":"user","content":question})
            answer = self._client.messages_create(
                model=self.chat_model, max_tokens=512,
                messages=self._history, system=system,
            )
            self._history.append({"role":"assistant","content":answer})

            if remember:
                self._rag.append(f"Q: {question}\nA: {answer}")

            return {
                "answer": answer, "route": f"GRAPH ({self.mode})",
                "router_ms": router_ms, "retrieval_ms": retrieval_ms,
                "total_ms": int((time.time()-t0)*1000),
                "rag_context": None, "rlm_meta": None,
                "graph_stats": self._graph.stats(),
            }

        elif route == "RLM_GRAPH":
            # RLM + Graph hybrid path
            t1 = time.time()
            rlm_graph_result = self._rlm_graph.retrieve(question, self._client)
            retrieval_ms = int((time.time()-t1)*1000)
            answer = rlm_graph_result["answer"]

            if remember:
                self._rag.append(f"Q: {question}\nA: {answer}")

            return {
                "answer": answer, "route": f"RLM+GRAPH ({self.mode})",
                "router_ms": router_ms, "retrieval_ms": retrieval_ms,
                "total_ms": int((time.time()-t0)*1000),
                "rag_context": None,
                "rlm_meta": {
                    "chunks_processed": rlm_graph_result["chunks_processed"],
                    "relevant_chunks": rlm_graph_result["relevant_chunks"],
                    "sub_summaries": rlm_graph_result["sub_summaries"],
                },
                "graph_stats": {
                    "entities": rlm_graph_result["graph_entities"],
                    "relationships": rlm_graph_result["graph_relationships"],
                },
            }

        elif route == "FOCUSED":
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
