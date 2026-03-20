# soul.py 🧠

[![PyPI version](https://img.shields.io/pypi/v/soul-agent.svg)](https://pypi.org/project/soul-agent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/soul-agent.svg)](https://pypi.org/project/soul-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Featured on Shipit](https://img.shields.io/badge/Shipit-Featured-6B4FBB?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMiAxNWwtNS01IDEuNDEtMS40MUwxMCAxNC4xN2w3LjU5LTcuNTlMMTkgOGwtOSA5eiIvPjwvc3ZnPg==)](https://www.shipit.buzz/products/soulpy)
[![Product Hunt](https://img.shields.io/badge/Product%20Hunt-Featured-DA552F?logo=producthunt&logoColor=white)](https://www.producthunt.com/@menonpg)
[![Amazon Book](https://img.shields.io/badge/📚_Book-Amazon-FF9900?logo=amazon&logoColor=white)](https://a.co/d/02T0WadG)

[![Star History](https://starchart.cc/menonpg/soul.py.svg)](https://starchart.cc/menonpg/soul.py)

**Your AI forgets everything when the conversation ends. soul.py fixes that.**

> 📖 **NEW: The book is out!** *Soul: Building AI Agents That Remember Who They Are* — everything here + deep dives on identity, memory patterns, multi-agent coordination, and the philosophy of persistent AI. **[Get it on Amazon →](https://a.co/d/02T0WadG)**

```python
from hybrid_agent import HybridAgent

agent = HybridAgent()
agent.ask("My name is Prahlad and I'm building an AI research lab.")

# New process. New session. Memory persists.
agent = HybridAgent()
result = agent.ask("What do you know about me?")
print(result["answer"])
# → "You're Prahlad, building an AI research lab."
```

No database. No server. Just markdown files and smart retrieval.

---

## ▶ Live Demos

| Version | Demo | What it shows |
|---|---|---|
| v0.1 | [soul.themenonlab.com](https://soul.themenonlab.com) | Memory persists across sessions |
| v1.0 | [soulv1.themenonlab.com](https://soulv1.themenonlab.com) | Semantic RAG retrieval |
| v2.0 | [soulv2.themenonlab.com](https://soulv2.themenonlab.com) | Auto query routing: RAG + RLM |
| **v0.2.0** | — | Modulizer: 50% token savings, zero-deps |
| **Ask Darwin** | [soul-book.themenonlab.com](https://soul-book.themenonlab.com) | 📖 Book companion — watch routing decisions live |

---

## 📚 The Book

**[Soul: Building AI Agents That Remember Who They Are](https://a.co/d/02T0WadG)**

The complete guide to persistent AI memory. Covers:
- Why agents forget (and the architectural fix)
- Identity vs Memory (SOUL.md vs MEMORY.md)
- RAG vs RLM (when to use each)
- Multi-agent memory sharing
- Darwinian evolution of agent identity
- Working code in every chapter

**[→ Available on Amazon](https://a.co/d/02T0WadG)**

---

## 📚 Documentation & Blog

| Topic | Link |
|-------|------|
| **Getting Started** | [Persistent Memory for LLM Agents](https://blog.themenonlab.com/blog/soul-py-persistent-memory-llm-agents/) |
| **v2.0 Architecture** | [RAG + RLM Hybrid — How It Works](https://blog.themenonlab.com/blog/soul-py-v2-rag-rlm-hybrid/) |
| **Comparison** | [soul.py vs mem0 vs Zep vs Letta](https://blog.themenonlab.com/blog/soul-py-vs-mem0-zep-letta-agent-memory/) |
| **Token Efficiency** | [v0.2.0 Modulizer — Token Savings](https://blog.themenonlab.com/blog/soul-py-v020-modulizer-token-savings/) |
| **Agent Identity** | [Darwin: Evolution, Identity, and AI Agents](https://blog.themenonlab.com/blog/soul-py-darwin-evolution-agent-identity/) |
| **LangChain / LlamaIndex** | [soul.py Integrations Guide](https://blog.themenonlab.com/blog/langchain-llamaindex-soul-integrations/) |
| **Enterprise** | [Is soul.py Enterprise-Ready?](https://blog.themenonlab.com/blog/soul-py-enterprise-what-is-ready/) |


## Install

```bash
pip install soul-agent
pip install soul-agent[anthropic]
pip install soul-agent[openai]
pip install soul-agent[gemini]   # ✅ Now available!
```

---

## 🆕 v0.2.0 — Modulizer (50% Token Savings)

Large MEMORY.md files burn tokens. **Modulizer** splits them into indexed modules and retrieves only what's relevant.

```bash
# Split your memory into modules
soul modulize MEMORY.md

# Creates:
# modules/INDEX.md (1.7KB)
# modules/projects.md
# modules/tools.md
# ...
```

**Two-phase retrieval:**
1. Read INDEX.md (always small)
2. LLM picks relevant modules
3. Load only those modules

**Results:** 47% fewer tokens on 25KB MEMORY.md. Zero infrastructure — no vector DB, no embeddings.

```python
from soul import Agent

agent = Agent(use_modules=True)  # default when modules exist
response = agent.ask("What tools have I used?")

# Check what was loaded
stats = agent.get_memory_stats()
# {'mode': 'modules', 'modules_read': ['tools.md'], 'total_kb': 5.5}
```

**CLI commands:**
- `soul modulize <file>` — split into modules
- `soul modules list` — view modules
- `soul chat --no-modules` — disable (opt-out)

**[Full writeup →](https://blog.themenonlab.com/blog/soul-py-v020-modulizer-token-savings)**

---

## Quickstart

```bash
soul init   # creates SOUL.md and MEMORY.md
```

```python
# v0.1 — simple markdown memory (great starting point)
from soul import Agent
agent = Agent(provider="anthropic")
agent.ask("Remember this.")

# v2.0 — automatic RAG + RLM routing (this repo's default)
from hybrid_agent import HybridAgent
agent = HybridAgent()  # auto-detects best retrieval per query
result = agent.ask("What do you know about me?")
print(result["answer"])
print(result["route"])   # "RAG" or "RLM"
```

## Multi-Provider Support

soul.py works with **any LLM provider** — no SDK lock-in:

```python
# Anthropic (default)
agent = HybridAgent(provider="anthropic")  # Uses ANTHROPIC_API_KEY

# Google Gemini
agent = HybridAgent(
    provider="gemini",
    chat_model="gemini-2.5-pro",       # or gemini-2.0-flash, gemini-2.5-flash
    router_model="gemini-2.0-flash",   # keep router cheap
)  # Uses GEMINI_API_KEY

# OpenAI
agent = HybridAgent(provider="openai")  # Uses OPENAI_API_KEY

# Local via Ollama
agent = HybridAgent(
    provider="openai-compatible",
    base_url="http://localhost:11434/v1",
    chat_model="llama3.2",
)
```

| Provider | Default Model | Env Var |
|----------|---------------|---------|
| `anthropic` | claude-haiku-4-5 | `ANTHROPIC_API_KEY` |
| `gemini` | gemini-2.0-flash | `GEMINI_API_KEY` |
| `openai` | gpt-4o-mini | `OPENAI_API_KEY` |
| `openai-compatible` | llama3.2 | `OPENAI_API_KEY` (optional) |

---

## ☁️ SoulMate API — Managed Cloud Option

Don't want to manage local files? **SoulMate API** gives you persistent memory as a service:

```python
from soulmate import SoulMateClient

# Sign up at soulmate-api.themenonlab.com/docs
client = SoulMateClient(
    api_key="sm_live_...",
    anthropic_key="sk-ant-..."  # BYOK — your own Anthropic key
)

# That's it. Memory persists in the cloud.
response = client.ask("My name is Prahlad.")
response = client.ask("What's my name?")  # → "Prahlad"
```

| Local (soul.py) | Cloud (SoulMate API) |
|---|---|
| Files on your machine | Managed cloud storage |
| You control everything | Zero infrastructure |
| Git-versioned memory | API-based, instant setup |
| Free forever | Free tier available |

**Get started:** [soulmate-api.themenonlab.com/docs](https://soulmate-api.themenonlab.com/docs)

---

## How it works

soul.py uses two markdown files as persistent state:

| File | Purpose |
|---|---|
| `SOUL.md` | Identity — who the agent is, how it behaves |
| `MEMORY.md` | Memory — timestamped log of every exchange |

**v2.0 adds a query router** that automatically dispatches to the right retrieval strategy:

```
Your query
    ↓
Router (fast LLM call)
    ├── FOCUSED  (~90%) → RAG — vector search, sub-second
    └── EXHAUSTIVE (~10%) → RLM — recursive synthesis, thorough
```

Architecture based on: [RAG + RLM: The Complete Knowledge Base Architecture](https://blog.themenonlab.com/blog/rag-plus-rlm-complete-knowledge-base-architecture)

---

## Branches

| Branch | Description | Best for |
|---|---|---|
| `main` | v2.0 — RAG + RLM hybrid (default) | Production use |
| `v2.0-rag-rlm` | Same as main, versioned | Pinning to v2 |
| `v1.0-rag` | RAG only, no RLM | Simpler setup |
| `v0.1-stable` | Pure markdown, zero deps | Learning / prototyping |

---

## v2.0 API

```python
result = agent.ask("What is my name?")

result["answer"]        # the response
result["route"]         # "RAG" or "RLM"
result["router_ms"]     # router latency
result["retrieval_ms"]  # retrieval latency
result["total_ms"]      # total latency
result["rag_context"]   # retrieved chunks (RAG path)
result["rlm_meta"]      # chunk stats (RLM path)
```

## v2.0 Setup

```python
agent = HybridAgent(
    soul_path="SOUL.md",
    memory_path="MEMORY.md",
    mode="auto",                    # "auto" | "rag" | "rlm"
    qdrant_url="...",               # or set QDRANT_URL env var
    qdrant_api_key="...",           # or QDRANT_API_KEY
    azure_embedding_endpoint="...", # or AZURE_EMBEDDING_ENDPOINT
    azure_embedding_key="...",      # or AZURE_EMBEDDING_KEY
    k=5,                            # RAG retrieval count
)
```

Falls back to BM25 (keyword) if Qdrant/Azure not configured.

---

## 📚 Knowledge Bases + Memory

soul.py isn't just for personal memory — the same architecture works for custom knowledge bases. Combine both in a single agent:

```python
agent = HybridAgent(
    soul_path="SOUL.md",
    memory_path="MEMORY.md",        # Per-user memory
    knowledge_dir="./knowledge",     # Your corpus (docs, products, policies)
)

# Index your knowledge base once
agent.index_knowledge()

# Now the agent searches both pools
agent.ask("What's the return policy?")         # → Knowledge base
agent.ask("What was I asking about earlier?")  # → User memory
agent.ask("Which product fits my needs?")      # → Both
```

**Example use cases:**

| Agent Type | Knowledge Base | Memory |
|------------|---------------|--------|
| **Support Bot** | Product docs, policies, FAQs | Customer history, preferences |
| **Research Assistant** | Paper corpus, methodologies | User's focus, papers read |
| **Onboarding Buddy** | Company handbook, org chart | New hire's role, questions |
| **Book Companion** | Full book content | Reader's interests, progress |

Darwin (the AI companion for the Soul book) uses exactly this pattern — the entire book indexed as knowledge, plus per-reader conversation memory.

See the [Memory Architecture Patterns](https://github.com/menonpg/soul-book) guide for detailed implementation patterns.

---

## 🔌 Framework Integrations

Already using a framework? Drop in soul.py memory with one line:

| Framework | Package | Install |
|-----------|---------|---------|
| **LangChain** | [langchain-soul](https://github.com/menonpg/langchain-soul) | `pip install langchain-soul` |
| **LlamaIndex** | [llamaindex-soul](https://github.com/menonpg/llamaindex-soul) | `pip install llamaindex-soul` |
| **CrewAI** | [crewai-soul](https://github.com/menonpg/crewai-soul) | `pip install crewai-soul` |

```python
# LangChain
from langchain_soul import SoulChatMessageHistory
history = SoulChatMessageHistory(session_id="user-123")

# LlamaIndex
from llamaindex_soul import SoulChatStore
chat_store = SoulChatStore()

# CrewAI
from crewai_soul import SoulMemory
memory = SoulMemory()
```

Each integration includes:
- **soul-agent** — RAG + RLM hybrid retrieval
- **soul-schema** — Database semantic layer (auto-document your tables)
- **SoulMate client** — Managed cloud option

---

## Why not LangChain / LlamaIndex / MemGPT?

Those are orchestration frameworks. soul.py is a primitive — persistent identity and memory you can drop into anything you're building.

- **No framework lock-in** — works with any LLM provider, or *with* your favorite framework via integrations above
- **Human-readable** — SOUL.md and MEMORY.md are plain text
- **Version-controllable** — git diff your agent's memories
- **Composable** — use just the parts you need

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and how to contribute.

---

## License

MIT

## Citation

```bibtex
@software{menon2026soul,
  author = {Menon, Prahlad G.},
  title  = {soul.py: Persistent Identity and Memory for LLM Agents},
  year   = {2026},
  url    = {https://github.com/menonpg/soul.py}
}
```
