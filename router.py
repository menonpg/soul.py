"""
soul.py v2.0 — Query Router
Classifies queries as FOCUSED or EXHAUSTIVE.
Works with any client that has a messages_create() method.
"""
import time

ROUTER_PROMPT = """Classify this query for a memory retrieval system:
"{query}"

FOCUSED: Specific lookup (name, fact, date, single topic)
EXHAUSTIVE: Needs synthesis across many memories (patterns, summaries, all, every, compare, across)

Reply with exactly one word: FOCUSED or EXHAUSTIVE"""

def classify(query: str, client, model: str = "claude-haiku-4-5") -> dict:
    t0 = time.time()
    result = client.messages_create(
        model=model, max_tokens=5,
        messages=[{"role":"user","content":ROUTER_PROMPT.format(query=query)}],
    )
    latency = int((time.time()-t0)*1000)
    route = "EXHAUSTIVE" if "EXHAUSTIVE" in result.upper() else "FOCUSED"
    return {"route": route, "latency_ms": latency}
