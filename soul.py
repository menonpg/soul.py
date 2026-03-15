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
from typing import Optional

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
        modules_dir: Optional[str] = None,
        use_modules: bool = True,
    ):
        self.soul_path   = Path(soul_path)
        self.memory_path = Path(memory_path)
        self.provider    = provider.lower()
        self.api_key     = api_key
        self.model       = model
        self.base_url    = base_url
        self._history    = []
        self._last_query = None
        self._last_memory_meta = None
        
        # Modules support
        self.use_modules = use_modules
        if modules_dir:
            self.modules_dir = Path(modules_dir)
        else:
            self.modules_dir = self.memory_path.parent / "modules"

        self._ensure_files()
        self._client = self._build_client()
        self._modular_memory = None
        
        # Initialize modular memory if modules exist
        if self.use_modules and (self.modules_dir / "INDEX.md").exists():
            from modular_memory import ModularMemory
            self._modular_memory = ModularMemory(
                memory_path=str(self.memory_path),
                modules_dir=str(self.modules_dir),
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
            )

    # ── File management ──────────────────────────────────────────────────────

    def _ensure_files(self):
        if not self.soul_path.exists():
            self.soul_path.write_text(DEFAULT_SOUL)
        if not self.memory_path.exists():
            self.memory_path.write_text(DEFAULT_MEMORY)

    def _read_soul(self):
        return self.soul_path.read_text().strip()

    def _read_memory(self, query: Optional[str] = None):
        """
        Read memory, using modules if available.
        
        Args:
            query: The user's query (used for module selection)
        """
        # Use modular memory if available and query provided
        if self._modular_memory and query:
            content, meta = self._modular_memory.retrieve(query)
            self._last_memory_meta = meta
            return content
        
        # Fallback to full memory
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
        
        self._last_memory_meta = {"mode": "full", "total_kb": round(len(text.encode()) / 1024, 2)}
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
                # For openai-compatible (Ollama, etc.), use dummy key if none provided
                # Ollama ignores the key, but OpenAI library requires something
                key = self.api_key or os.environ.get("OPENAI_API_KEY")
                if not key and self.provider == "openai-compatible":
                    key = "ollama"  # Dummy key for local endpoints
                return OpenAI(
                    api_key=key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError("pip install openai")
        else:
            raise ValueError(f"Unknown provider: {self.provider!r}. Use 'anthropic', 'openai', or 'openai-compatible'.")

    # ── Prompt construction ───────────────────────────────────────────────────

    def _system_prompt(self, query: Optional[str] = None):
        return f"{self._read_soul()}\n\n---\n\n# Your Memory\n{self._read_memory(query)}"

    # ── LLM call ──────────────────────────────────────────────────────────────

    def _call(self, messages, query: Optional[str] = None):
        system = self._system_prompt(query)
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
