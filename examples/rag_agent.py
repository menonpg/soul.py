"""
soul.py v1.0 — RAG backend example.
Handles large memory files (thousands of entries) via ChromaDB + local embeddings.

Install: pip install soul-agent[rag]
         pip install chromadb sentence-transformers
"""
from soul import RAGAgent

# Same API as v0.1 — retrieval is invisible
agent = RAGAgent(k=5)  # retrieve top 5 relevant memories per query

agent.ask("My name is Prahlad. I'm an AI researcher in Pittsburgh.")
agent.ask("I'm working on persistent memory architectures for LLM agents.")

# Even with 10,000 memory entries, only the 5 most relevant
# are injected — context window stays manageable
response = agent.ask("What do you know about my research?")
print(response)
print(f"\nMemory entries indexed: {agent._rag.count() if agent._rag else 'N/A'}")
