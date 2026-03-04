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
| 🔜 | **Gemini / Vertex AI** | text-embedding-004, multimodal |
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
| 🔜 | **Google Gemini** | gemini-pro, gemini-1.5-pro, gemini-1.5-flash |
| 🔲 | LangChain | Memory backend |
| 🔲 | LlamaIndex | Integration |
| 🔲 | n8n | Official node |

---

## GCP / Google Cloud Support

| Status | Feature | Notes |
|--------|---------|-------|
| 🔜 | Gemini models | Full provider support |
| 🔜 | Vertex AI embeddings | text-embedding-004 |
| 🔲 | Cloud Storage backend | GCS for memory persistence |
| 🔲 | Cloud Run deployment | One-click deploy |
| 🔲 | Firebase integration | Real-time sync |

**Why GCP?** Many teams are GCP-native and want to stay within Google's ecosystem. Full Gemini support means soul.py works without any OpenAI/Anthropic dependencies.

---

## Contributing

Have an idea? Open an issue or submit a PR. All contributions welcome.

See the [GitHub Issues](https://github.com/menonpg/soul.py/issues) for current priorities.
