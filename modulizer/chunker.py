"""Chunker — Split markdown into logical chunks based on headers."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    """A logical chunk of markdown content."""
    header: str           # The header text (e.g., "## Projects")
    level: int            # Header level (1-6)
    content: str          # Full content including header
    line_start: int       # Starting line number
    line_end: int         # Ending line number
    
    @property
    def size_bytes(self) -> int:
        return len(self.content.encode('utf-8'))
    
    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024


def chunk_markdown(content: str, min_chunk_lines: int = 3) -> List[Chunk]:
    """
    Split markdown content into chunks based on headers.
    
    Args:
        content: The full markdown content
        min_chunk_lines: Minimum lines for a valid chunk
        
    Returns:
        List of Chunk objects
    """
    lines = content.split('\n')
    chunks: List[Chunk] = []
    
    # Pattern to match markdown headers (## Header, ### Header, etc.)
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    
    current_chunk_start = 0
    current_header = ""
    current_level = 0
    
    for i, line in enumerate(lines):
        match = header_pattern.match(line)
        if match:
            # Save previous chunk if it has content
            if i > current_chunk_start:
                chunk_content = '\n'.join(lines[current_chunk_start:i])
                if chunk_content.strip() and (i - current_chunk_start) >= min_chunk_lines:
                    chunks.append(Chunk(
                        header=current_header or "(preamble)",
                        level=current_level or 0,
                        content=chunk_content,
                        line_start=current_chunk_start,
                        line_end=i - 1
                    ))
            
            # Start new chunk
            current_chunk_start = i
            current_level = len(match.group(1))
            current_header = match.group(2).strip()
    
    # Don't forget the last chunk
    if current_chunk_start < len(lines):
        chunk_content = '\n'.join(lines[current_chunk_start:])
        if chunk_content.strip():
            chunks.append(Chunk(
                header=current_header or "(preamble)",
                level=current_level or 0,
                content=chunk_content,
                line_start=current_chunk_start,
                line_end=len(lines) - 1
            ))
    
    return chunks


def merge_small_chunks(chunks: List[Chunk], min_size_kb: float = 1.0) -> List[Chunk]:
    """
    Merge consecutive small chunks that are under the minimum size.
    
    Args:
        chunks: List of chunks to process
        min_size_kb: Minimum size in KB before merging
        
    Returns:
        List of merged chunks
    """
    if not chunks:
        return []
    
    merged: List[Chunk] = []
    current = chunks[0]
    
    for next_chunk in chunks[1:]:
        # If current chunk is small and same level, merge with next
        if current.size_kb < min_size_kb and current.level == next_chunk.level:
            current = Chunk(
                header=current.header,
                level=current.level,
                content=current.content + '\n\n' + next_chunk.content,
                line_start=current.line_start,
                line_end=next_chunk.line_end
            )
        else:
            merged.append(current)
            current = next_chunk
    
    merged.append(current)
    return merged
