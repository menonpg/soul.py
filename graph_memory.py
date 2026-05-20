"""
soul.py — Graph Memory
Two modes:
  1. "llm"   — LLM-based entity/relationship extraction (higher quality, costs tokens)
  2. "regex" — Regex-based extraction (zero LLM calls, fast, free)

Both build an in-memory knowledge graph from MEMORY.md entries.
Can be combined with RLM for RLM+Graph hybrid retrieval.
"""

import re
import time
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ── Regex-based entity/relationship extraction ────────────────────────────────

# Common patterns for extracting structured info from markdown memory entries
_PATTERNS = {
    # "X is Y" / "X was Y" / "X are Y"
    "is_a": re.compile(
        r'(?:^|\.\s+)([A-Z][A-Za-z0-9_\- ]{1,40})\s+(?:is|was|are)\s+(?:a|an|the)?\s*([A-Za-z0-9_\- ]{2,60})',
        re.MULTILINE
    ),
    # "X uses Y"
    "uses": re.compile(
        r'([A-Z][A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,3})\s+uses?\s+([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})',
        re.IGNORECASE
    ),
    # "X deployed to Y" / "X published to Y"
    "deployed_to": re.compile(
        r'([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})\s+(?:deployed|published|pushed|shipped)\s+(?:to|on)\s+([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})',
        re.IGNORECASE
    ),
    # "X depends on Y" / "X requires Y"
    "depends_on": re.compile(
        r'([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})\s+(?:depends on|requires|needs)\s+([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})',
        re.IGNORECASE
    ),
    # "X created Y" / "X built Y"
    "created": re.compile(
        r'([A-Z][A-Za-z0-9_\-]+(?:\s[A-Za-z0-9_\-]+){0,2})\s+(?:created|built|wrote|made|developed)\s+([A-Za-z0-9_\.\-]+(?:\s[A-Za-z0-9_\.\-]+){0,2})',
        re.IGNORECASE
    ),
    # "X version Y" / "X vY.Z"
    "version": re.compile(
        r'([A-Za-z0-9_\.\-]{2,30})\s+v?(\d+\.\d+(?:\.\d+)?)',
    ),
    # Key-value from markdown: **Key:** Value or `key`: value
    "property": re.compile(
        r'(?:\*\*([A-Za-z0-9_ ]+)\*\*|`([A-Za-z0-9_]+)`)\s*[:=]\s*(.+?)(?:\n|$)',
    ),
    # URLs associated with entities
    "url": re.compile(
        r'([A-Za-z0-9_\.\- ]{2,30})\s*(?:→|->|:)\s*(https?://\S+)',
    ),
    # "X → Y" / "X -> Y" (explicit relationships)
    "arrow": re.compile(
        r'([A-Za-z0-9_\.\- ]{2,40})\s*(?:→|->)\s*([A-Za-z0-9_\.\- ]{2,40})',
    ),
}

# Skip these as entities (too generic)
_STOPWORDS = {
    'the', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'its',
    'we', 'our', 'you', 'your', 'they', 'them', 'he', 'she', 'what',
    'which', 'who', 'how', 'when', 'where', 'why', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'not', 'only', 'same', 'so', 'than', 'too', 'very',
    'can', 'will', 'just', 'should', 'now', 'also', 'new', 'first',
    'status', 'feature', 'notes', 'done', 'todo', 'update', 'changes',
}


def _clean_entity(text):
    """Normalize entity name."""
    text = text.strip().strip('*`"\'')
    # Remove trailing punctuation
    text = re.sub(r'[.,;:!?]+$', '', text)
    if text.lower() in _STOPWORDS or len(text) < 2:
        return None
    return text


def extract_regex(text):
    """
    Extract entities and relationships from text using regex patterns.
    Returns: list of (subject, relation, object) triples.
    """
    triples = []

    for rel_type, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            if rel_type == "property":
                subj = _clean_entity(match.group(1) or match.group(2))
                obj = _clean_entity(match.group(3))
                if subj and obj:
                    triples.append((subj, "has_property", obj))
            else:
                subj = _clean_entity(match.group(1))
                obj = _clean_entity(match.group(2))
                if subj and obj and subj.lower() != obj.lower():
                    triples.append((subj, rel_type, obj))

    return triples


# ── LLM-based entity/relationship extraction ─────────────────────────────────

_EXTRACT_PROMPT = """Extract entities and relationships from this memory entry.
Return ONLY lines in this format (one per line):
ENTITY|subject|relation|object

Relations should be short verbs/prepositions: uses, is_a, deployed_to, depends_on, created, version, related_to, etc.

Entry:
{text}

Extract all meaningful relationships. Be concise. No commentary."""


def extract_llm(text, client, model="claude-haiku-4-5"):
    """
    Extract entities and relationships using an LLM.
    Returns: list of (subject, relation, object) triples.
    """
    response = client.messages_create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": _EXTRACT_PROMPT.format(text=text)}],
    )

    triples = []
    for line in response.strip().split('\n'):
        line = line.strip()
        if line.startswith("ENTITY|"):
            parts = line.split("|")
            if len(parts) >= 4:
                subj = _clean_entity(parts[1])
                rel = parts[2].strip().lower().replace(' ', '_')
                obj = _clean_entity(parts[3])
                if subj and obj:
                    triples.append((subj, rel, obj))

    return triples


# ── Knowledge Graph ───────────────────────────────────────────────────────────

class KnowledgeGraph:
    """
    In-memory knowledge graph built from extracted triples.
    Supports querying by entity, relationship, or natural language.
    """

    def __init__(self):
        # adjacency: entity -> [(relation, target, source_entry_hash)]
        self.adj = defaultdict(list)
        # reverse index: entity -> set of entry hashes it appears in
        self.entity_entries = defaultdict(set)
        # entry hash -> original text
        self.entries = {}
        # all entities (normalized lowercase -> display form)
        self.entities = {}

    def _norm(self, entity):
        return entity.lower().strip()

    def add_triples(self, triples, source_text):
        """Add extracted triples linked to their source entry."""
        entry_hash = hashlib.md5(source_text.encode()).hexdigest()[:12]
        self.entries[entry_hash] = source_text

        for subj, rel, obj in triples:
            sn = self._norm(subj)
            on = self._norm(obj)

            self.entities[sn] = subj
            self.entities[on] = obj

            self.adj[sn].append((rel, on, entry_hash))
            self.adj[on].append((rel + "_inv", sn, entry_hash))

            self.entity_entries[sn].add(entry_hash)
            self.entity_entries[on].add(entry_hash)

    def query_entity(self, entity, max_hops=2):
        """
        Get all relationships for an entity (up to max_hops).
        Returns: dict with relationships and source entries.
        """
        en = self._norm(entity)
        if en not in self.adj:
            # Fuzzy match
            matches = [k for k in self.entities if entity.lower() in k or k in entity.lower()]
            if matches:
                en = matches[0]
            else:
                return {"entity": entity, "found": False, "relationships": [], "sources": []}

        visited = set()
        relationships = []
        source_hashes = set()

        def _traverse(node, depth):
            if depth > max_hops or node in visited:
                return
            visited.add(node)
            for rel, target, entry_hash in self.adj.get(node, []):
                if not rel.endswith("_inv"):
                    relationships.append({
                        "subject": self.entities.get(node, node),
                        "relation": rel,
                        "object": self.entities.get(target, target),
                    })
                source_hashes.add(entry_hash)
                if depth < max_hops:
                    _traverse(target, depth + 1)

        _traverse(en, 0)

        sources = [self.entries[h] for h in source_hashes if h in self.entries]

        return {
            "entity": self.entities.get(en, entity),
            "found": True,
            "relationships": relationships,
            "sources": sources[:5],  # limit source entries
        }

    def query_text(self, query):
        """
        Find relevant graph context for a natural language query.
        Extracts entity mentions from the query and traverses the graph.
        """
        # Tokenize query, find matching entities
        words = re.findall(r'[A-Za-z0-9_\.\-]+', query)
        matched_entities = set()

        for word in words:
            wl = word.lower()
            if wl in _STOPWORDS or len(wl) < 3:
                continue
            for ent in self.entities:
                if wl in ent or ent in wl:
                    matched_entities.add(ent)

        # Also try multi-word matches
        query_lower = query.lower()
        for ent in self.entities:
            if len(ent) > 3 and ent in query_lower:
                matched_entities.add(ent)

        if not matched_entities:
            return {"matches": [], "context": "No matching entities found in graph."}

        all_rels = []
        all_sources = set()
        for ent in matched_entities:
            result = self.query_entity(ent, max_hops=1)
            if result["found"]:
                all_rels.extend(result["relationships"])
                for s in result["sources"]:
                    all_sources.add(s[:500])  # truncate long entries

        # Deduplicate relationships
        seen = set()
        unique_rels = []
        for r in all_rels:
            key = (r["subject"].lower(), r["relation"], r["object"].lower())
            if key not in seen:
                seen.add(key)
                unique_rels.append(r)

        # Format context
        if unique_rels:
            rel_text = "\n".join(
                f"- {r['subject']} —[{r['relation']}]→ {r['object']}"
                for r in unique_rels[:20]
            )
            context = f"## Graph relationships\n{rel_text}"
        else:
            context = "No relationships found."

        return {
            "matches": list(matched_entities),
            "relationships": unique_rels,
            "context": context,
            "sources": list(all_sources)[:5],
        }

    def stats(self):
        return {
            "entities": len(self.entities),
            "edges": sum(len(v) for v in self.adj.values()) // 2,  # halve for inv
            "entries_indexed": len(self.entries),
        }


# ── GraphMemory — main interface ──────────────────────────────────────────────

class GraphMemory:
    """
    Graph-based memory for soul.py.

    Modes:
        "regex" — Fast, free, no LLM calls. Uses pattern matching.
        "llm"   — Higher quality extraction using LLM. Costs tokens.

    Usage:
        gm = GraphMemory(mode="regex")
        gm.build()  # Index MEMORY.md
        result = gm.retrieve("What tools does soul.py use?")
    """

    def __init__(
        self,
        memory_path="MEMORY.md",
        mode="regex",           # "regex" | "llm"
        llm_client=None,        # Required for mode="llm"
        llm_model="claude-haiku-4-5",
    ):
        self.memory_path = Path(memory_path)
        self.mode = mode
        self._client = llm_client
        self._model = llm_model
        self.graph = KnowledgeGraph()
        self._indexed = set()

        if mode == "llm" and not llm_client:
            raise ValueError("llm_client required for mode='llm'")

    def _parse_entries(self):
        if not self.memory_path.exists():
            return []
        text = self.memory_path.read_text()
        parts = re.split(r'\n(?=## )', text)
        return [p.strip() for p in parts if p.strip() and not p.strip().startswith("# MEMORY")]

    def build(self):
        """Index all entries from MEMORY.md into the knowledge graph."""
        entries = self._parse_entries()
        new_entries = [e for e in entries if e not in self._indexed]

        for entry in new_entries:
            if self.mode == "llm":
                triples = extract_llm(entry, self._client, self._model)
            else:
                triples = extract_regex(entry)

            self.graph.add_triples(triples, entry)
            self._indexed.add(entry)

        return self.graph.stats()

    def retrieve(self, query, k=5):
        """
        Query the graph for relevant context.
        Returns formatted string suitable for LLM context.
        """
        self.build()  # Ensure indexed

        result = self.graph.query_text(query)

        if not result["relationships"]:
            return f"No graph relationships found for: '{query}'"

        parts = [result["context"]]
        if result.get("sources"):
            parts.append("\n## Source entries")
            for s in result["sources"][:k]:
                parts.append(f"\n---\n{s}")

        return "\n".join(parts)

    def stats(self):
        return self.graph.stats()


# ── RLM + Graph Hybrid ───────────────────────────────────────────────────────

class RLMGraphMemory:
    """
    Combines RLM (recursive synthesis) with knowledge graph context.
    Graph provides structured relationships; RLM does exhaustive synthesis.
    The graph context is injected into each RLM sub-call for better relevance.

    Usage:
        from graph_memory import RLMGraphMemory
        rgm = RLMGraphMemory(mode="regex")  # or mode="llm"
        result = rgm.retrieve("What's the status of soul.py?", client)
    """

    def __init__(
        self,
        memory_path="MEMORY.md",
        mode="regex",           # Graph mode: "regex" | "llm"
        chunk_size=10,
        sub_model="claude-haiku-4-5",
        synth_model="claude-haiku-4-5",
    ):
        self.memory_path = Path(memory_path)
        self.chunk_size = chunk_size
        self.sub_model = sub_model
        self.synth_model = synth_model
        self._graph = None
        self._graph_mode = mode

    def _ensure_graph(self, client=None):
        if self._graph is None:
            self._graph = GraphMemory(
                memory_path=self.memory_path,
                mode=self._graph_mode,
                llm_client=client if self._graph_mode == "llm" else None,
                llm_model=self.sub_model,
            )
            self._graph.build()

    def _parse_entries(self):
        text = self.memory_path.read_text()
        return [b.strip() for b in re.split(r'\n## ', text)[1:] if b.strip()]

    def retrieve(self, query: str, client) -> dict:
        """
        Retrieve with RLM + Graph hybrid.
        1. Build/query knowledge graph for structured context
        2. Run RLM recursive synthesis with graph context injected
        3. Synthesize final answer from both
        """
        t0 = time.time()

        # Step 1: Graph context
        self._ensure_graph(client)
        graph_result = self._graph.graph.query_text(query)
        graph_context = graph_result.get("context", "")

        # Step 2: RLM with graph-enhanced prompts
        entries = self._parse_entries()

        if not entries and not graph_result.get("relationships"):
            return {
                "answer": "No memories found yet.",
                "chunks_processed": 0, "relevant_chunks": 0,
                "graph_entities": 0, "graph_relationships": 0,
                "latency_ms": 0, "sub_summaries": [],
            }

        chunks = [entries[i:i + self.chunk_size]
                  for i in range(0, len(entries), self.chunk_size)]

        # Inject graph context into sub-prompts for better relevance
        graph_hint = ""
        if graph_context and graph_context != "No relationships found.":
            graph_hint = f"\n\nKnown relationships from knowledge graph:\n{graph_context}\n"

        sub_summaries = []
        for chunk in chunks:
            chunk_text = "\n\n---\n".join(chunk)
            summary = client.messages_create(
                model=self.sub_model, max_tokens=400,
                messages=[{"role": "user", "content":
                    f"From these memory entries, extract ONLY what's relevant to:\n'{query}'\n"
                    f"{graph_hint}\n"
                    f"Entries:\n{chunk_text}\n\nBe concise. If nothing relevant, reply: SKIP"
                }],
            )
            if summary.upper() != "SKIP":
                sub_summaries.append(summary)

        # Step 3: Synthesize with graph + RLM
        if not sub_summaries and not graph_result.get("relationships"):
            return {
                "answer": f"No memories relevant to: '{query}'",
                "chunks_processed": len(chunks), "relevant_chunks": 0,
                "graph_entities": len(graph_result.get("matches", [])),
                "graph_relationships": len(graph_result.get("relationships", [])),
                "latency_ms": int((time.time() - t0) * 1000),
                "sub_summaries": [],
            }

        combined_parts = []
        if graph_context and graph_context != "No relationships found.":
            combined_parts.append(f"Knowledge graph:\n{graph_context}")
        if sub_summaries:
            combined_parts.append(f"Memory synthesis:\n" + "\n\n===\n".join(sub_summaries))

        combined = "\n\n---\n\n".join(combined_parts)

        answer = client.messages_create(
            model=self.synth_model, max_tokens=600,
            messages=[{"role": "user", "content":
                f"Synthesize into a complete answer to: '{query}'\n\n"
                f"Findings (from knowledge graph + memory entries):\n{combined}\n\n"
                f"Be direct. Use relationships from the graph to structure your answer."
            }],
        )

        stats = self._graph.stats()
        return {
            "answer": answer,
            "chunks_processed": len(chunks),
            "relevant_chunks": len(sub_summaries),
            "graph_entities": stats["entities"],
            "graph_relationships": stats["edges"],
            "latency_ms": int((time.time() - t0) * 1000),
            "sub_summaries": sub_summaries,
        }
