"""
soul.py — Persistent identity and memory for any LLM agent.
v0.1: markdown-native, zero infrastructure, provider-agnostic.

Usage:
    from soul import Agent
    agent = Agent()
    response = agent.ask("What should I focus on today?")

Reads SOUL.md (identity) and MEMORY.md (long-term memory) from the
current directory. Writes new memories back after each exchange.
Works with OpenAI, Anthropic, or any OpenAI-compatible endpoint.
"""

import os
from datetime import datetime
from pathlib import Path

DEFAULT_SOUL = """\
# SOUL.md
You are a helpful, persistent AI assistant.
You have opinions. You remember things. You are not a generic chatbot.
"""

DEFAULT_MEMORY = """\
# MEMORY.md
(No memories yet.)
"""

MAX_MEMORY_CHARS = 6000
MAX_RESPONSE_TOKENS = 1024


class Agent:
    """
    A persistent agent backed by SOUL.md and MEMORY.md.

    Args:
        soul_path:   Path to SOUL.md  (created with defaults if missing)
        memory_path: Path to MEMORY.md (created with defaults if missing)
        provider:    "anthropic" | "openai" | "openai-compatible"
        api_key:     API key (falls back to env vars)
        model:       Model name override
        base_url:    Base URL for openai-compatible endpoints (e.g. Ollama)
    """

    def __init__(
        self,
        soul_path="SOUL.md",
        memory_path="MEMORY.md",
        provider="anthropic",
        api_key=None,
        model=None,
        base_url=None,
    ):
        self.soul_path   = Path(soul_path)
        self.memory_path = Path(memory_path)
        self.provider    = provider.lower()
        self.api_key     = api_key
        self.model       = model
        self.base_url    = base_url
        self._history    = []

        self._ensure_files()
        self._client = self._build_client()

    # ── File management ──────────────────────────────────────────────────────

    def _ensure_files(self):
        if not self.soul_path.exists():
            self.soul_path.write_text(DEFAULT_SOUL)
        if not self.memory_path.exists():
            self.memory_path.write_text(DEFAULT_MEMORY)

    def _read_soul(self):
        return self.soul_path.read_text().strip()

    def _read_memory(self):
        text = self.memory_path.read_text().strip()
        if len(text) > MAX_MEMORY_CHARS:
            lines = text.splitlines()
            kept, size = [], 0
            for line in reversed(lines):
                size += len(line) + 1
                if size > MAX_MEMORY_CHARS:
                    break
                kept.insert(0, line)
            text = "[... earlier memories truncated — see MEMORY.md for full history ...]\n" + "\n".join(kept)
        return text

    def _append_memory(self, exchange):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## {ts}\n{exchange.strip()}\n"
        with open(self.memory_path, "a") as f:
            f.write(entry)

    # ── LLM client ────────────────────────────────────────────────────────────

    def _build_client(self):
        if self.provider == "anthropic":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key or os.environ.get("ANTHROPIC_API_KEY"))
            except ImportError:
                raise ImportError("pip install anthropic")
        elif self.provider in ("openai", "openai-compatible"):
            try:
                from openai import OpenAI
                return OpenAI(
                    api_key=self.api_key or os.environ.get("OPENAI_API_KEY"),
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError("pip install openai")
        else:
            raise ValueError(f"Unknown provider: {self.provider!r}. Use 'anthropic', 'openai', or 'openai-compatible'.")

    # ── Prompt construction ───────────────────────────────────────────────────

    def _system_prompt(self):
        return f"{self._read_soul()}\n\n---\n\n# Your Memory\n{self._read_memory()}"

    # ── LLM call ──────────────────────────────────────────────────────────────

    def _call(self, messages):
        system = self._system_prompt()
        if self.provider == "anthropic":
            model = self.model or "claude-sonnet-4-6"
            resp = self._client.messages.create(
                model=model,
                max_tokens=MAX_RESPONSE_TOKENS,
                system=system,
                messages=messages,
            )
            return resp.content[0].text.strip()
        else:
            model = self.model or "gpt-4o"
            resp = self._client.chat.completions.create(
                model=model,
                max_tokens=MAX_RESPONSE_TOKENS,
                messages=[{"role": "system", "content": system}] + messages,
            )
            return resp.choices[0].message.content.strip()

    # ── Public API ────────────────────────────────────────────────────────────

    def ask(self, question, remember=True):
        """Ask the agent a question. Persists to MEMORY.md by default."""
        self._history.append({"role": "user", "content": question})
        response = self._call(self._history)
        self._history.append({"role": "assistant", "content": response})
        if remember:
            self._append_memory(f"Q: {question}\nA: {response}")
        return response

    def reset_conversation(self):
        """Clear in-session history (does not affect MEMORY.md)."""
        self._history = []

    def remember(self, note):
        """Manually write a note to MEMORY.md."""
        self._append_memory(note)


# ── v1.0 RAG extension ────────────────────────────────────────────────────────

class RAGAgent(Agent):
    """
    soul.py v1.0 — Agent with RAG memory backend.
    Handles MEMORY.md files with thousands of entries.
    Falls back to flat injection if chromadb not installed.

    Usage:
        agent = RAGAgent("SOUL.md", k=5)
        agent.ask("What did I say about my research last week?")
    """

    def __init__(self, soul_path="SOUL.md", memory_path="MEMORY.md",
                 provider="anthropic", api_key=None, model=None,
                 base_url=None, k=5):
        # Initialize base without building client yet
        self.k = k
        self._rag = None
        super().__init__(soul_path, memory_path, provider, api_key, model, base_url)

        # Try to init RAG memory
        try:
            from rag_memory import RAGMemory
            self._rag = RAGMemory(str(self.memory_path), k=k)
        except ImportError:
            pass  # graceful fallback to flat memory

    def _read_memory(self):
        if self._rag:
            # Return placeholder — retrieve() is called per-query
            return "[RAG memory active — context retrieved per query]"
        return super()._read_memory()

    def _system_prompt(self, query: str = "") -> str:
        soul = self._read_soul()
        if self._rag and query:
            memory = self._rag.retrieve(query)
        else:
            memory = super()._read_memory()
        return f"{soul}\n\n---\n\n{memory}"

    def _call(self, messages):
        # Pass query to system prompt for RAG retrieval
        query = messages[-1]["content"] if messages else ""
        system = self._system_prompt(query)

        if self.provider == "anthropic":
            model = self.model or "claude-sonnet-4-6"
            resp = self._client.messages.create(
                model=model, max_tokens=MAX_RESPONSE_TOKENS,
                system=system, messages=messages,
            )
            return resp.content[0].text.strip()
        else:
            model = self.model or "gpt-4o"
            resp = self._client.chat.completions.create(
                model=model, max_tokens=MAX_RESPONSE_TOKENS,
                messages=[{"role": "system", "content": system}] + messages,
            )
            return resp.choices[0].message.content.strip()

    def _append_memory(self, exchange):
        if self._rag:
            self._rag.append(exchange)
        else:
            super()._append_memory(exchange)
