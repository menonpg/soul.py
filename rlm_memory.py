"""
soul.py v2.0 — RLM Memory
Recursive synthesis for exhaustive queries.
Works with AnthropicREST client (messages_create method).
"""
import re, time
from pathlib import Path


class RLMMemory:
    def __init__(self, memory_path="MEMORY.md", chunk_size=10,
                 sub_model="claude-haiku-4-5", synth_model="claude-haiku-4-5"):
        self.memory_path = Path(memory_path)
        self.chunk_size = chunk_size
        self.sub_model = sub_model
        self.synth_model = synth_model

    def _parse_entries(self):
        text = self.memory_path.read_text()
        return [b.strip() for b in re.split(r'\n## ', text)[1:] if b.strip()]

    def retrieve(self, query: str, client) -> dict:
        t0 = time.time()
        entries = self._parse_entries()

        if not entries:
            return {"answer": "No memories found yet.",
                    "chunks_processed": 0, "relevant_chunks": 0,
                    "latency_ms": 0, "sub_summaries": []}

        chunks = [entries[i:i+self.chunk_size]
                  for i in range(0, len(entries), self.chunk_size)]

        sub_summaries = []
        for chunk in chunks:
            chunk_text = "\n\n---\n".join(chunk)
            summary = client.messages_create(
                model=self.sub_model, max_tokens=400,
                messages=[{"role":"user","content":
                    f"From these memory entries, extract ONLY what's relevant to:\n'{query}'\n\n"
                    f"Entries:\n{chunk_text}\n\nBe concise. If nothing relevant, reply: SKIP"
                }],
            )
            if summary.upper() != "SKIP":
                sub_summaries.append(summary)

        if not sub_summaries:
            return {"answer": f"No memories relevant to: '{query}'",
                    "chunks_processed": len(chunks), "relevant_chunks": 0,
                    "latency_ms": int((time.time()-t0)*1000), "sub_summaries": []}

        combined = "\n\n===\n".join(sub_summaries)
        answer = client.messages_create(
            model=self.synth_model, max_tokens=600,
            messages=[{"role":"user","content":
                f"Synthesize into a complete answer to: '{query}'\n\nFindings:\n{combined}\n\nBe direct."
            }],
        )

        return {
            "answer": answer,
            "chunks_processed": len(chunks),
            "relevant_chunks": len(sub_summaries),
            "latency_ms": int((time.time()-t0)*1000),
            "sub_summaries": sub_summaries,
        }
