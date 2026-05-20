"""Lightweight entity graph for conversation memory.

Pure stdlib — no external dependencies. Extracts entity-relationship triples
from conversation text via regex patterns and optional LLM calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


# Common stop words to exclude from entity detection
_STOP = {
    "I", "He", "She", "It", "We", "They", "You", "The", "This", "That",
    "My", "His", "Her", "Our", "Your", "Their", "Its", "What", "When",
    "Where", "Who", "How", "Why", "Which", "There", "Here", "Also",
    "But", "And", "Yes", "No", "Not", "Just", "Very", "Really", "Actually",
    "Maybe", "Well", "Oh", "So", "Then", "Now", "Today", "Tomorrow",
    "Yesterday", "Sure", "Thanks", "Thank", "Please", "Sorry", "Hey",
    "Hi", "Hello", "Bye", "Ok", "Okay", "Right", "Yeah", "Yep", "Nope",
    "Good", "Great", "Nice", "Cool", "Wow", "Like", "Think", "Know",
    "Want", "Need", "Would", "Could", "Should", "Will", "Can", "May",
    "Some", "Any", "All", "Each", "Every", "Much", "Many", "Few",
    "Date", "Session", "Speaker", "User", "Assistant",
}

# Regex patterns: (pattern, relationship, subject_group, object_group)
_PATTERNS: list[tuple[str, str, int, int]] = [
    # Name patterns
    (r"(?:my |his |her )?name is (\w+)", "name", 0, 1),
    # Location
    (r"(\w+) (?:lives?|living) in ([A-Z][\w\s,]+?)(?:\.|,|$)", "lives_in", 1, 2),
    (r"(\w+) (?:moved|moving) to ([A-Z][\w\s,]+?)(?:\.|,|$)", "lives_in", 1, 2),
    (r"(\w+) (?:is |was )?from ([A-Z][\w\s,]+?)(?:\.|,|$)", "from", 1, 2),
    # Work
    (r"(\w+) (?:works?|working) (?:at|for) ([A-Z][\w\s&]+?)(?:\.|,|$)", "works_at", 1, 2),
    (r"(\w+)(?:'s| is a| is an) ([\w\s]+?)(?:\.|,|$)", "occupation", 1, 2),
    # Allergies
    (r"(\w+) (?:is )?allergic to ([\w\s]+?)(?:\.|,|$)", "allergic_to", 1, 2),
    # Birth / age
    (r"(\w+) (?:was )?born (?:in|on) ([\w\s,]+?)(?:\.|,|$)", "born", 1, 2),
    # Likes / preferences
    (r"(\w+) (?:likes?|loves?|enjoys?) ([\w\s]+?)(?:\.|,|$)", "likes", 1, 2),
    (r"(\w+)(?:'s)? favou?rite (\w+) is ([\w\s]+?)(?:\.|,|$)", "favorite", 1, 3),
    # Relationships
    (r"(\w+) (?:is )?married to (\w+)", "married_to", 1, 2),
    (r"(\w+)(?:'s)? (?:wife|husband|spouse|partner) (?:is )?(\w+)", "married_to", 1, 2),
    # Possessions / family
    (r"(\w+) has (?:a |an )?([\w\s]+?)(?:\.|,|$)", "has", 1, 2),
]

_LLM_PROMPT = (
    "Extract all entity-relationship triples from this conversation.\n"
    "Format: one triple per line as: SUBJECT | RELATIONSHIP | OBJECT | TIMESTAMP (if known)\n"
    "Examples:\n"
    "  John | lives_in | Austin | 2026-03\n"
    "  Mary | works_at | Google |\n"
    "Only extract factual statements. Be concise. No commentary.\n\n"
    "Conversation:\n{text}"
)


class GraphMemory:
    """Lightweight entity graph extracted from conversation text."""

    def __init__(
        self,
        graph_path: str = "MEMORY.graph.json",
        llm_client: Any = None,
        llm_model: str | None = None,
    ):
        self.graph_path = Path(graph_path)
        self.llm_client = llm_client
        self.llm_model = llm_model
        self._graph: dict = {"entities": {}, "edges": []}
        if self.graph_path.exists():
            try:
                self._graph = json.loads(self.graph_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    # ── Storage ──────────────────────────────────────────────

    def extract_and_store(self, text: str) -> None:
        """Extract entities and relationships from text, append to graph."""
        # Detect current timestamp from conversation headers
        ts_match = re.search(r"\[Date:\s*([^\]]+)\]", text)
        current_ts = ts_match.group(1).strip() if ts_match else ""

        # Step 1: Regex extraction
        triples = self._regex_extract(text, current_ts)

        # Step 2: Proper noun detection (capitalized words appearing 2+ times)
        proper_nouns = self._detect_proper_nouns(text)
        for noun in proper_nouns:
            self._ensure_entity(noun, "unknown")

        # Step 3: LLM extraction (optional)
        if self.llm_client and self.llm_model:
            llm_triples = self._llm_extract(text)
            triples.extend(llm_triples)

        # Step 4: Merge into graph
        for src, rel, dst, ts in triples:
            src, dst = src.strip(), dst.strip()
            if not src or not dst or len(src) < 2 or len(dst) < 2:
                continue
            self._ensure_entity(src, self._guess_type(rel, "src"))
            self._ensure_entity(dst, self._guess_type(rel, "dst"))
            self._add_edge(src, rel, dst, ts or current_ts)

        self._save()

    def _regex_extract(self, text: str, default_ts: str) -> list[tuple[str, str, str, str]]:
        triples = []
        for pattern, rel, sg, og in _PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    src = m.group(sg) if sg > 0 else "User"
                    obj = m.group(og)
                    triples.append((src.strip(), rel, obj.strip(), default_ts))
                except (IndexError, AttributeError):
                    continue
        return triples

    def _llm_extract(self, text: str) -> list[tuple[str, str, str, str]]:
        """Use LLM to extract triples."""
        triples = []
        # Truncate to avoid huge context
        truncated = text[:4000] if len(text) > 4000 else text
        prompt = _LLM_PROMPT.format(text=truncated)
        try:
            response = self.llm_client.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.0,
            )
            # Parse response lines
            resp_text = ""
            if isinstance(response, dict):
                # Handle different response formats
                if "choices" in response:
                    resp_text = response["choices"][0].get("message", {}).get("content", "")
                elif "content" in response:
                    content = response["content"]
                    if isinstance(content, list):
                        resp_text = content[0].get("text", "") if content else ""
                    else:
                        resp_text = str(content)
                elif "candidates" in response:
                    candidates = response["candidates"]
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        resp_text = parts[0].get("text", "") if parts else ""
            elif isinstance(response, str):
                resp_text = response

            for line in resp_text.strip().splitlines():
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    ts = parts[3] if len(parts) > 3 else ""
                    triples.append((parts[0], parts[1], parts[2], ts))
        except Exception:
            pass  # LLM extraction is best-effort
        return triples

    def _detect_proper_nouns(self, text: str) -> list[str]:
        """Find capitalized words appearing 2+ times."""
        words = re.findall(r"\b([A-Z][a-z]{2,})\b", text)
        counts: dict[str, int] = {}
        for w in words:
            if w not in _STOP:
                counts[w] = counts.get(w, 0) + 1
        return [w for w, c in counts.items() if c >= 2]

    def _ensure_entity(self, name: str, etype: str) -> None:
        ents = self._graph["entities"]
        if name in ents:
            ents[name]["mentions"] = ents[name].get("mentions", 0) + 1
        else:
            ents[name] = {"type": etype, "mentions": 1}

    def _guess_type(self, rel: str, role: str) -> str:
        if rel in ("lives_in", "from", "born") and role == "dst":
            return "location"
        if rel in ("works_at",) and role == "dst":
            return "organization"
        if role == "src":
            return "person"
        return "unknown"

    def _add_edge(self, src: str, rel: str, dst: str, ts: str) -> None:
        edges = self._graph["edges"]
        # Deduplicate
        for e in edges:
            if e["src"] == src and e["rel"] == rel and e["dst"] == dst:
                if ts and not e.get("ts"):
                    e["ts"] = ts
                return
        edges.append({"src": src, "rel": rel, "dst": dst, "ts": ts, "confidence": 0.9})

    def _save(self) -> None:
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(json.dumps(self._graph, indent=2))

    # ── Retrieval ────────────────────────────────────────────

    def retrieve(self, question: str) -> str:
        """Retrieve relevant subgraph for a question."""
        if not self._graph["edges"]:
            return ""

        # Extract query entities
        query_entities = set()
        # Capitalized words
        for w in re.findall(r"\b([A-Z][a-z]{2,})\b", question):
            if w not in _STOP:
                query_entities.add(w)
        # Also try lowercase matching against known entities
        q_lower = question.lower()
        for ent in self._graph["entities"]:
            if ent.lower() in q_lower:
                query_entities.add(ent)

        if not query_entities:
            # Fallback: return all edges (small graph)
            if len(self._graph["edges"]) <= 20:
                return self._format_edges(self._graph["edges"])
            return ""

        # Walk 1-2 hops
        hop1_entities = set(query_entities)
        relevant_edges = []
        for e in self._graph["edges"]:
            if e["src"] in query_entities or e["dst"] in query_entities:
                relevant_edges.append(e)
                hop1_entities.add(e["src"])
                hop1_entities.add(e["dst"])

        # Hop 2
        for e in self._graph["edges"]:
            if e not in relevant_edges:
                if e["src"] in hop1_entities or e["dst"] in hop1_entities:
                    relevant_edges.append(e)

        # Temporal sorting for time questions
        temporal_keywords = {"when", "what time", "how long", "date", "year", "month"}
        if any(kw in q_lower for kw in temporal_keywords):
            relevant_edges.sort(key=lambda e: e.get("ts", ""), reverse=True)

        return self._format_edges(relevant_edges)

    def _format_edges(self, edges: list[dict]) -> str:
        if not edges:
            return ""
        lines = ["Entity Graph Context:"]
        for e in edges:
            line = f"- {e['src']} {e['rel']} {e['dst']}"
            if e.get("ts"):
                line += f" (timestamp: {e['ts']})"
            lines.append(line)
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset the graph."""
        self._graph = {"entities": {}, "edges": []}
        if self.graph_path.exists():
            self.graph_path.unlink()
