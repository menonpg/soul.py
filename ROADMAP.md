# Roadmap 🗺️

Planned features and improvements for soul.py. PRs welcome!

---

## 🧬 soul-schema (v0.1.0 SHIPPED! 🎉)

A standalone PyPI library for auto-generating semantic layers from any database — the "portable Unity Catalog."

**Install:** `pip install soul-schema`  
**Repo:** [github.com/menonpg/soul-schema](https://github.com/menonpg/soul-schema)

| Status | Feature | Notes |
|--------|---------|-------|
| ✅ | PyPI package | `pip install soul-schema` |
| ✅ | Multi-database | Postgres, MySQL, SQLite (any SQLAlchemy) |
| ✅ | Auto-descriptions | LLM-powered from metadata |
| ✅ | Learning loop | Locked corrections never overwritten |
| ✅ | dbt YAML export | `soul-schema export --format dbt` |
| ✅ | Vanna export | `soul-schema export --format vanna` |
| ✅ | Air-gapped | Full Ollama support |
| 🔲 | JOIN inference | Learn relationships from usage |

**Why?** Teams without Unity Catalog need a way to build semantic metadata for Text-to-SQL. soul-schema uses soul.py's memory primitive to remember what columns mean and get smarter over time.

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
| 🔲 | **Modulizer (zero-deps)** | Auto-segment large files into indexed modules |
| 🔲 | Auto summarization | Compress old memories |
| 🔲 | Importance scoring | Prioritize key facts |
| 🔲 | Tiered memory | Hot/warm/cold storage |
| 🔲 | Archive-before-prune | Index to vector DB before deleting old files |
| 🔲 | Frozen storage | S3/GCS backup hook for disaster recovery |
| 🔲 | Export/import | Backup & restore |

---

## 📦 Modulizer (Zero-Deps Memory Segmentation)

**Problem:** Users with large knowledge bases (100KB+ in a single MEMORY.md) face:
- High token costs (AI reads everything every query)
- Slow response times
- Missed information in long documents

**Solution:** `soul modulize` command that auto-segments large files into indexed modules.

| Status | Feature | Notes |
|--------|---------|-------|
| 🔲 | `soul modulize` CLI | Segment large .md files into modules |
| 🔲 | Auto-categorization | LLM-powered topic detection |
| 🔲 | INDEX.md generation | TOC with module summaries |
| 🔲 | Smart retrieval | Read index → pull relevant module only |
| 🔲 | Merge/split tools | Reorganize modules over time |

**How it works:**
```bash
soul modulize brain-dump.md --output ./modules/
# Creates:
#   modules/INDEX.md (table of contents)
#   modules/expertise-map.md
#   modules/career-timeline.md
#   modules/offer-architecture.md
#   ... (auto-detected categories)
```

**Why?** For v0.1 (pure markdown) users who don't want vector databases, this provides ~90% of RAG's token savings with zero infrastructure. The AI reads the lightweight INDEX.md, identifies which module(s) it needs, and pulls only those.

**Trade-offs vs RAG:**
- ✅ Zero dependencies (no Qdrant, no embeddings)
- ✅ Human-readable/editable modules
- ❌ No semantic search (category-based, not concept-based)
- ❌ Cross-cutting queries may miss relevant modules

**Best for:** Solo creators, personal knowledge bases, air-gapped deployments, prototype agents.

---

## Integrations

| Status | Integration | Notes |
|--------|-------------|-------|
| ✅ | Anthropic Claude | Native support |
| ✅ | OpenAI | Native support |
| ✅ | Ollama | OpenAI-compatible API |
| ✅ | **Google Gemini** | gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro (v0.1.6) |
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

---

## Retrieval Enhancements

| Status | Feature | Notes |
|--------|---------|-------|
| 🔲 | LLM Reranking | Score/filter RAG results before generation |
| 🔲 | Hybrid search | Combine BM25 + semantic scores |
| 🔲 | Query expansion | LLM rewrites query for better recall |
| 🔲 | Snippet extraction | Dynamic context windows around matches |
