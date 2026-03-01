"""
soul.py v2.0 — Query Router (RAG + RLM Hybrid)
Based on: https://blog.themenonlab.com/blog/rag-plus-rlm-complete-knowledge-base-architecture

Routes queries to the appropriate memory retrieval strategy:
  FOCUSED  (~90%) → RAG  — fast vector search, sub-second
  EXHAUSTIVE (~10%) → RLM — recursive decomposition, handles "summarize all..."

The router is a single lightweight LLM call.
"""
import re

ROUTER_PROMPT = """Classify this query for a memory retrieval system:

Query: {query}

Categories:
- FOCUSED: Looking for specific information (name, fact, decision, event)
- EXHAUSTIVE: Needs analysis across many memories (patterns, summaries, comparisons)

Indicators of EXHAUSTIVE: "all", "every", "across", "compare", "pattern", "summarize", "overall"
Indicators of FOCUSED: specific names, dates, topics, "what did I say about X"

Respond with exactly one word: FOCUSED or EXHAUSTIVE"""


def classify_query(query: str, client, model: str = "claude-haiku-4-5") -> str:
    """Returns 'FOCUSED' or 'EXHAUSTIVE'. Fast, cheap single call."""
    resp = client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
    )
    result = resp.content[0].text.strip().upper()
    return "EXHAUSTIVE" if "EXHAUSTIVE" in result else "FOCUSED"


class RLMMemory:
    """
    v2.0 RLM path — recursive decomposition for exhaustive queries.
    Instead of retrieving top-k chunks, the LLM navigates memory recursively.

    For queries like:
      "What patterns appear in my decisions?"
      "Summarize everything I've said about my research"
      "Compare my thoughts on X vs Y across all sessions"
    """

    def __init__(self, memory_path: str = "MEMORY.md", chunk_size: int = 20):
        from pathlib import Path
        self.memory_path = Path(memory_path)
        self.chunk_size = chunk_size  # entries per recursive sub-call

    def _parse_entries(self) -> list[str]:
        """Split MEMORY.md into individual entries."""
        text = self.memory_path.read_text()
        blocks = re.split(r'\n## ', text)
        return [b.strip() for b in blocks[1:] if b.strip()]

    def retrieve(self, query: str, client, model: str = "claude-haiku-4-5") -> str:
        """
        Recursively process memory in chunks, synthesize into final answer.
        Each chunk produces a summary; summaries are aggregated.
        """
        entries = self._parse_entries()
        if not entries:
            return "No memories found."

        # Split into chunks
        chunks = [entries[i:i+self.chunk_size]
                  for i in range(0, len(entries), self.chunk_size)]

        # Sub-call: summarize each chunk relative to the query
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_text = "\n\n---\n".join(chunk)
            resp = client.messages.create(
                model=model,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": f"From these memory entries, extract anything relevant to: '{query}'\n\nEntries:\n{chunk_text}\n\nBe concise. If nothing relevant, say 'nothing relevant'."
                }]
            )
            summary = resp.content[0].text.strip()
            if "nothing relevant" not in summary.lower():
                chunk_summaries.append(summary)

        if not chunk_summaries:
            return f"No relevant memories found for: {query}"

        # Final synthesis across all chunk summaries
        all_summaries = "\n\n".join(chunk_summaries)
        final = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": f"Synthesize these findings to answer: '{query}'\n\nFindings:\n{all_summaries}"
            }]
        )
        return final.content[0].text.strip()
