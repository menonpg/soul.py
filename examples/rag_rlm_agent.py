"""
soul.py v2.0 — RAG + RLM Hybrid Agent

Query router dispatches automatically:
  FOCUSED  → RAG (fast, cheap, sub-second)
  EXHAUSTIVE → RLM (recursive, thorough, handles "summarize all...")

Architecture: blog.themenonlab.com/blog/rag-plus-rlm-complete-knowledge-base-architecture
"""
from soul import RAGAgent
from router import classify_query, RLMMemory

class HybridAgent(RAGAgent):
    """
    v2.0: Adds RLM path on top of RAG.
    Same agent.ask() API — routing is invisible.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rlm = RLMMemory(str(self.memory_path))

    def ask(self, question, remember=True):
        # Classify query
        route = classify_query(question, self._client)
        print(f"[Router: {route}]")  # visible in demo/debug

        if route == "EXHAUSTIVE":
            # RLM path: recursive synthesis across all memory
            answer = self._rlm.retrieve(question, self._client)
        else:
            # RAG path: fast vector retrieval
            self._history.append({"role": "user", "content": question})
            answer = self._call(self._history)
            self._history.append({"role": "assistant", "content": answer})

        if remember:
            self._append_memory(f"Q: {question}\nA: {answer}")
        return answer


# Usage
agent = HybridAgent(k=5)

# FOCUSED → RAG (fast)
agent.ask("My name is Prahlad. I'm an AI researcher.")
agent.ask("What is my name?")  # → RAG

# EXHAUSTIVE → RLM (recursive)
agent.ask("What patterns appear across everything I've told you?")  # → RLM
agent.ask("Summarize all my research topics")  # → RLM
