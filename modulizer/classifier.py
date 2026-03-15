"""Classifier — LLM-powered topic detection for chunks."""

import os
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass

from .chunker import Chunk


@dataclass 
class ClassifiedChunk:
    """A chunk with its assigned category."""
    chunk: Chunk
    category: str
    confidence: float
    keywords: List[str]


# Default categories for memory content
DEFAULT_CATEGORIES = [
    "projects",      # Active and past projects
    "tools",         # Tools, technologies, configurations
    "people",        # Contacts, collaborators, relationships
    "decisions",     # Key decisions and reasoning
    "learnings",     # Lessons learned, insights
    "procedures",    # How-to guides, workflows
    "ideas",         # Backlog, future plans, brainstorms
    "reference",     # Facts, data, lookups
]


def classify_chunks(
    chunks: List[Chunk],
    categories: Optional[List[str]] = None,
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> List[ClassifiedChunk]:
    """
    Classify chunks into categories using LLM.
    
    Args:
        chunks: List of chunks to classify
        categories: Custom category list (uses defaults if None)
        provider: LLM provider (anthropic, openai, gemini, openai-compatible)
        model: Model name (uses provider default if None)
        api_key: API key (uses env var if None)
        base_url: Base URL for compatible providers
        
    Returns:
        List of ClassifiedChunk objects
    """
    categories = categories or DEFAULT_CATEGORIES
    
    # Build classification prompt
    prompt = _build_classification_prompt(chunks, categories)
    
    # Call LLM
    response = _call_llm(prompt, provider, model, api_key, base_url)
    
    # Parse response into classifications
    return _parse_classifications(chunks, response, categories)


def _build_classification_prompt(chunks: List[Chunk], categories: List[str]) -> str:
    """Build the classification prompt."""
    
    chunks_text = ""
    for i, chunk in enumerate(chunks):
        preview = chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content
        chunks_text += f"\n---CHUNK {i}---\nHeader: {chunk.header}\n{preview}\n"
    
    return f"""Classify each chunk into exactly one category. Return JSON array.

Categories: {', '.join(categories)}

{chunks_text}

Return a JSON array with one object per chunk:
[
  {{"chunk_id": 0, "category": "projects", "confidence": 0.9, "keywords": ["keyword1", "keyword2"]}},
  ...
]

Only return the JSON array, no other text."""


def _call_llm(
    prompt: str,
    provider: str,
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
) -> str:
    """Call the LLM API and return response text."""
    
    if provider == "anthropic":
        return _call_anthropic(prompt, model, api_key)
    elif provider == "openai":
        return _call_openai(prompt, model, api_key, base_url)
    elif provider == "gemini":
        return _call_gemini(prompt, model, api_key)
    elif provider == "openai-compatible":
        return _call_openai(prompt, model, api_key, base_url)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_anthropic(prompt: str, model: Optional[str], api_key: Optional[str]) -> str:
    """Call Anthropic Claude API."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    model = model or "claude-sonnet-4-20250514"
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def _call_openai(
    prompt: str, 
    model: Optional[str], 
    api_key: Optional[str],
    base_url: Optional[str]
) -> str:
    """Call OpenAI or compatible API."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    base_url = base_url or "https://api.openai.com/v1"
    model = model or "gpt-4o"
    
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, model: Optional[str], api_key: Optional[str]) -> str:
    """Call Google Gemini API."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
    
    model = model or "gemini-2.0-flash"
    
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"Content-Type": "application/json"},
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_classifications(
    chunks: List[Chunk],
    response: str,
    categories: List[str]
) -> List[ClassifiedChunk]:
    """Parse LLM response into ClassifiedChunk objects."""
    
    # Extract JSON from response (handle markdown code blocks)
    json_str = response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("```")[1]
        if json_str.startswith("json"):
            json_str = json_str[4:]
    
    try:
        classifications = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: assign all to "reference" category
        return [
            ClassifiedChunk(
                chunk=chunk,
                category="reference",
                confidence=0.5,
                keywords=[]
            )
            for chunk in chunks
        ]
    
    result = []
    for i, chunk in enumerate(chunks):
        # Find classification for this chunk
        cls = next((c for c in classifications if c.get("chunk_id") == i), None)
        
        if cls:
            category = cls.get("category", "reference")
            # Validate category
            if category not in categories:
                category = "reference"
            
            result.append(ClassifiedChunk(
                chunk=chunk,
                category=category,
                confidence=cls.get("confidence", 0.5),
                keywords=cls.get("keywords", [])
            ))
        else:
            # Fallback
            result.append(ClassifiedChunk(
                chunk=chunk,
                category="reference",
                confidence=0.5,
                keywords=[]
            ))
    
    return result
