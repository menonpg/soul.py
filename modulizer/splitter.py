"""Splitter — Group classified chunks into modules."""

from typing import List, Dict
from dataclasses import dataclass
from collections import defaultdict

from .classifier import ClassifiedChunk


@dataclass
class Module:
    """A module containing related chunks."""
    name: str                      # Module filename (e.g., "projects.md")
    category: str                  # Category this module represents
    chunks: List[ClassifiedChunk]  # Chunks in this module
    
    @property
    def content(self) -> str:
        """Generate the full markdown content for this module."""
        lines = [f"# {self.category.title()}\n"]
        
        for classified in self.chunks:
            lines.append(classified.chunk.content)
            lines.append("")  # Blank line between sections
        
        return '\n'.join(lines)
    
    @property
    def size_kb(self) -> float:
        """Size of module in KB."""
        return len(self.content.encode('utf-8')) / 1024
    
    @property
    def chunk_count(self) -> int:
        """Number of chunks in this module."""
        return len(self.chunks)


def split_into_modules(
    classified_chunks: List[ClassifiedChunk],
    max_module_kb: float = 20.0,
    min_chunks_per_module: int = 2,
) -> List[Module]:
    """
    Group classified chunks into modules by category.
    
    Args:
        classified_chunks: List of chunks with categories
        max_module_kb: Maximum size per module (splits if exceeded)
        min_chunks_per_module: Minimum chunks before creating separate module
        
    Returns:
        List of Module objects
    """
    # Group chunks by category
    by_category: Dict[str, List[ClassifiedChunk]] = defaultdict(list)
    for cc in classified_chunks:
        by_category[cc.category].append(cc)
    
    modules = []
    misc_chunks = []  # For categories with too few chunks
    
    for category, chunks in by_category.items():
        if len(chunks) < min_chunks_per_module:
            # Too few chunks, add to misc
            misc_chunks.extend(chunks)
            continue
        
        # Check if we need to split due to size
        total_size = sum(c.chunk.size_kb for c in chunks)
        
        if total_size <= max_module_kb:
            # Single module for this category
            modules.append(Module(
                name=f"{category}.md",
                category=category,
                chunks=chunks
            ))
        else:
            # Split into multiple modules
            sub_modules = _split_large_category(category, chunks, max_module_kb)
            modules.extend(sub_modules)
    
    # Create misc module if there are orphan chunks
    if misc_chunks:
        modules.append(Module(
            name="misc.md",
            category="misc",
            chunks=misc_chunks
        ))
    
    return modules


def _split_large_category(
    category: str,
    chunks: List[ClassifiedChunk],
    max_kb: float
) -> List[Module]:
    """Split a large category into multiple numbered modules."""
    modules = []
    current_chunks = []
    current_size = 0.0
    part_num = 1
    
    for chunk in chunks:
        chunk_size = chunk.chunk.size_kb
        
        if current_size + chunk_size > max_kb and current_chunks:
            # Save current module and start new one
            modules.append(Module(
                name=f"{category}-{part_num}.md",
                category=category,
                chunks=current_chunks
            ))
            current_chunks = [chunk]
            current_size = chunk_size
            part_num += 1
        else:
            current_chunks.append(chunk)
            current_size += chunk_size
    
    # Don't forget the last module
    if current_chunks:
        if part_num == 1:
            # Only one module, no need for numbering
            modules.append(Module(
                name=f"{category}.md",
                category=category,
                chunks=current_chunks
            ))
        else:
            modules.append(Module(
                name=f"{category}-{part_num}.md",
                category=category,
                chunks=current_chunks
            ))
    
    return modules


def get_module_stats(modules: List[Module]) -> Dict:
    """Get statistics about the modules."""
    total_chunks = sum(m.chunk_count for m in modules)
    total_size = sum(m.size_kb for m in modules)
    
    return {
        "module_count": len(modules),
        "total_chunks": total_chunks,
        "total_size_kb": round(total_size, 2),
        "avg_module_size_kb": round(total_size / len(modules), 2) if modules else 0,
        "modules": [
            {
                "name": m.name,
                "category": m.category,
                "chunks": m.chunk_count,
                "size_kb": round(m.size_kb, 2)
            }
            for m in modules
        ]
    }
