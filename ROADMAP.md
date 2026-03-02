# Roadmap 🗺️

Planned features and improvements for soul.py. PRs welcome!

---

## Vector Database Support

| Status | Backend | Notes |
|--------|---------|-------|
| ✅ | Qdrant | Current default |
| ✅ | ChromaDB | Local, zero-config (v0.1.2) |
| 🔲 | pgvector | PostgreSQL native |
| 🔲 | FAISS | Local, fast |
| 🔲 | Pinecone | Cloud hosted |
| 🔲 | Weaviate | |

---

## Embedding Providers

| Status | Provider | Notes |
|--------|----------|-------|
| ✅ | Azure OpenAI | Current default |
| ✅ | OpenAI direct | v0.1.2 |
| 🔲 | Cohere | |
| 🔲 | sentence-transformers | Local embeddings |
| 🔲 | Ollama | Local via Ollama API |

---

## CLI & Developer Experience

| Status | Feature | Notes |
|--------|---------|-------|
| ✅ | `soul init` | Interactive setup wizard |
| ✅ | `soul chat` | Interactive CLI mode (v0.1.2) |
| ✅ | `soul status` | Memory stats & diagnostics (v0.1.2) |
| 🔲 | `config.yaml` | File-based configuration |
| 🔲 | VSCode extension | Syntax highlighting, previews |

---

## Memory Features

| Status | Feature | Notes |
|--------|---------|-------|
| ✅ | Timestamped logging | Conversation history |
| ✅ | RAG + RLM routing | Auto query classification |
| 🔲 | Auto summarization | Compress old memories |
| 🔲 | Importance scoring | Prioritize key facts |
| 🔲 | Tiered memory | Hot/warm/cold storage |
| 🔲 | Export/import | Backup & restore |

---

## Integrations

| Status | Integration | Notes |
|--------|-------------|-------|
| ✅ | Anthropic Claude | Native support |
| ✅ | OpenAI | Native support |
| ✅ | Ollama | OpenAI-compatible API |
| 🔲 | LangChain | Memory backend |
| 🔲 | LlamaIndex | Integration |
| 🔲 | n8n | Official node |

---

## Contributing

Have an idea? Open an issue or submit a PR. All contributions welcome.

See the [GitHub Issues](https://github.com/menonpg/soul.py/issues) for current priorities.
