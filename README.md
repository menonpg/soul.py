# soul.py 🧠

[![PyPI version](https://img.shields.io/pypi/v/soul-agent.svg)](https://pypi.org/project/soul-agent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/soul-agent.svg)](https://pypi.org/project/soul-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Your AI forgets everything when the conversation ends. soul.py fixes that.**

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
| **Ask Darwin** | [soul-book.themenonlab.com](https://soul-book.themenonlab.com) | 📖 Book companion — watch routing decisions live |

---

## Install

```bash
pip install soul-agent
pip install soul-agent[anthropic]
pip install soul-agent[openai]
```

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

---

## ☁️ SoulMate API — Managed Cloud Option

Don't want to manage local files? **SoulMate API** gives you persistent memory as a service:

```python
from soulmate import SoulMateClient

# Sign up at soulmate-api-production.up.railway.app/docs
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

**Get started:** [soulmate-api-production.up.railway.app/docs](https://soulmate-api-production.up.railway.app/docs)

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

## Why not LangChain / LlamaIndex / MemGPT?

Those are orchestration frameworks. soul.py is a primitive — persistent identity and memory you can drop into anything you're building.

- **No framework lock-in** — works with any LLM provider
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
