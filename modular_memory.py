"""
modular_memory.py — Two-phase retrieval for modulized memory.

When modules/INDEX.md exists, reads index first, then pulls only relevant modules.
Falls back to reading full MEMORY.md when no modules exist.
"""

import os
import requests
from pathlib import Path
from typing import List, Optional, Tuple


class ModularMemory:
    """
    Two-phase memory retrieval for modulized files.
    
    Phase 1: Read INDEX.md (small, ~2KB)
    Phase 2: LLM picks relevant modules, read only those
    
    Falls back to full MEMORY.md if no modules exist.
    """
    
    def __init__(
        self,
        memory_path: str = "MEMORY.md",
        modules_dir: str = "modules",
        provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_modules: int = 3,
        max_memory_chars: int = 6000,
    ):
        self.memory_path = Path(memory_path)
        self.modules_dir = Path(modules_dir)
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_modules = max_modules
        self.max_memory_chars = max_memory_chars
    
    @property
    def has_modules(self) -> bool:
        """Check if modulized memory exists."""
        index_path = self.modules_dir / "INDEX.md"
        return index_path.exists()
    
    def retrieve(self, query: str) -> Tuple[str, dict]:
        """
        Retrieve relevant memory for a query.
        
        Returns:
            (memory_content, metadata)
            
        metadata contains:
            - mode: "modules" or "full"
            - modules_read: list of module names (if modules mode)
            - total_kb: total KB read
        """
        if self.has_modules:
            return self._retrieve_from_modules(query)
        else:
            return self._retrieve_full()
    
    def _retrieve_full(self) -> Tuple[str, dict]:
        """Fallback: read full MEMORY.md."""
        if not self.memory_path.exists():
            return "(No memories yet.)", {"mode": "full", "total_kb": 0}
        
        content = self.memory_path.read_text().strip()
        
        # Truncate if too long
        if len(content) > self.max_memory_chars:
            lines = content.splitlines()
            kept, size = [], 0
            for line in reversed(lines):
                size += len(line) + 1
                if size > self.max_memory_chars:
                    break
                kept.insert(0, line)
            content = "[... earlier memories truncated ...]\n" + "\n".join(kept)
        
        return content, {
            "mode": "full",
            "total_kb": round(len(content.encode()) / 1024, 2)
        }
    
    def _retrieve_from_modules(self, query: str) -> Tuple[str, dict]:
        """Two-phase retrieval from modules."""
        # Phase 1: Read index
        index_path = self.modules_dir / "INDEX.md"
        index_content = index_path.read_text()
        
        # Get available modules
        modules = self._list_modules()
        
        # Phase 2: Ask LLM which modules are relevant
        relevant = self._pick_modules(query, index_content, modules)
        
        # Read selected modules
        combined = []
        total_bytes = len(index_content.encode())
        
        for module_name in relevant[:self.max_modules]:
            module_path = self.modules_dir / module_name
            if module_path.exists():
                content = module_path.read_text()
                combined.append(f"## From {module_name}\n{content}")
                total_bytes += len(content.encode())
        
        if not combined:
            # Fallback to index summary if no modules selected
            combined = [index_content]
        
        return "\n\n---\n\n".join(combined), {
            "mode": "modules",
            "modules_read": relevant[:self.max_modules],
            "total_kb": round(total_bytes / 1024, 2),
            "index_kb": round(len(index_content.encode()) / 1024, 2)
        }
    
    def _list_modules(self) -> List[str]:
        """List available module files."""
        if not self.modules_dir.exists():
            return []
        return [
            f.name for f in self.modules_dir.glob("*.md")
            if f.name != "INDEX.md"
        ]
    
    def _pick_modules(
        self, 
        query: str, 
        index_content: str, 
        modules: List[str]
    ) -> List[str]:
        """Use LLM to pick relevant modules for query."""
        
        if not modules:
            return []
        
        prompt = f"""Given this user query and memory index, which modules are most relevant?

USER QUERY: {query}

AVAILABLE MODULES: {', '.join(modules)}

INDEX:
{index_content[:2000]}

Return ONLY a comma-separated list of the {self.max_modules} most relevant module filenames.
Example: projects.md, tools.md

Relevant modules:"""

        try:
            response = self._call_llm(prompt)
            # Parse response
            selected = []
            for part in response.replace("\n", ",").split(","):
                name = part.strip()
                if name in modules:
                    selected.append(name)
            return selected if selected else modules[:1]  # Fallback to first module
        except Exception:
            # On error, return all modules (will be limited by max_modules)
            return modules[:self.max_modules]
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM to pick modules."""
        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.provider in ("openai", "openai-compatible"):
            return self._call_openai(prompt)
        elif self.provider == "gemini":
            return self._call_gemini(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _call_anthropic(self, prompt: str) -> str:
        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        model = self.model or "claude-sonnet-4-20250514"
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    
    def _call_openai(self, prompt: str) -> str:
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        base_url = self.base_url or "https://api.openai.com/v1"
        model = self.model or "gpt-4o-mini"
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def _call_gemini(self, prompt: str) -> str:
        api_key = self.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        model = self.model or "gemini-2.0-flash"
        
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def get_memory_content(
    query: str,
    memory_path: str = "MEMORY.md",
    modules_dir: str = "modules",
    provider: str = "anthropic",
    **kwargs
) -> Tuple[str, dict]:
    """
    Convenience function for retrieving memory.
    
    Automatically uses modules if available, falls back to full memory.
    """
    mm = ModularMemory(
        memory_path=memory_path,
        modules_dir=modules_dir,
        provider=provider,
        **kwargs
    )
    return mm.retrieve(query)
