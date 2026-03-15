"""Modulize — Main entry point for memory segmentation."""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .chunker import chunk_markdown, merge_small_chunks
from .classifier import classify_chunks, DEFAULT_CATEGORIES
from .splitter import split_into_modules, get_module_stats
from .indexer import generate_index


def modulize(
    input_path: str,
    output_dir: Optional[str] = None,
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    categories: Optional[List[str]] = None,
    max_module_kb: float = 20.0,
    min_chunks_per_module: int = 2,
    backup: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Modulize a large markdown file into indexed modules.
    
    Args:
        input_path: Path to the input markdown file (e.g., MEMORY.md)
        output_dir: Output directory for modules (default: ./modules/)
        provider: LLM provider (anthropic, openai, gemini, openai-compatible)
        model: Model name (uses provider default if None)
        api_key: API key (uses env var if None)
        base_url: Base URL for compatible providers
        categories: Custom category list (uses defaults if None)
        max_module_kb: Maximum size per module in KB
        min_chunks_per_module: Minimum chunks before creating separate module
        backup: Whether to backup original file
        dry_run: If True, only analyze without writing files
        verbose: Print progress messages
        
    Returns:
        Dict with stats and results
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Set output directory
    if output_dir is None:
        output_dir = input_file.parent / "modules"
    output_path = Path(output_dir)
    
    if verbose:
        print(f"\n🧠 soul.py modulizer")
        print(f"   Input:  {input_path}")
        print(f"   Output: {output_path}/")
        print()
    
    # Read input file
    content = input_file.read_text()
    original_size = len(content.encode('utf-8')) / 1024
    
    if verbose:
        print(f"📄 Reading {input_path} ({original_size:.1f} KB)")
    
    # Step 1: Chunk the markdown
    if verbose:
        print("📦 Chunking by headers...")
    chunks = chunk_markdown(content)
    chunks = merge_small_chunks(chunks, min_size_kb=0.5)
    
    if verbose:
        print(f"   Found {len(chunks)} chunks")
    
    # Step 2: Classify chunks
    if verbose:
        print(f"🏷️  Classifying chunks ({provider})...")
    classified = classify_chunks(
        chunks,
        categories=categories,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    
    # Step 3: Split into modules
    if verbose:
        print("📁 Grouping into modules...")
    modules = split_into_modules(
        classified,
        max_module_kb=max_module_kb,
        min_chunks_per_module=min_chunks_per_module,
    )
    
    stats = get_module_stats(modules)
    
    if verbose:
        print(f"   Created {len(modules)} modules:")
        for m in stats["modules"]:
            print(f"     - {m['name']}: {m['chunks']} sections, {m['size_kb']} KB")
    
    # Step 4: Generate index
    if verbose:
        print("📑 Generating INDEX.md...")
    index_content = generate_index(
        modules,
        original_file=input_file.name,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    
    if dry_run:
        if verbose:
            print("\n✨ Dry run complete. No files written.")
        return {
            "status": "dry_run",
            "original_size_kb": round(original_size, 2),
            "stats": stats,
            "index_preview": index_content[:500] + "...",
        }
    
    # Step 5: Write files
    if verbose:
        print("💾 Writing files...")
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Backup original if requested
    if backup:
        backup_path = input_file.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        shutil.copy(input_file, backup_path)
        if verbose:
            print(f"   Backed up to {backup_path}")
    
    # Write modules
    for module in modules:
        module_path = output_path / module.name
        module_path.write_text(module.content)
        if verbose:
            print(f"   ✓ {module.name}")
    
    # Write index
    index_path = output_path / "INDEX.md"
    index_path.write_text(index_content)
    if verbose:
        print(f"   ✓ INDEX.md")
    
    # Summary
    index_size = len(index_content.encode('utf-8')) / 1024
    savings = ((original_size - index_size) / original_size) * 100
    
    if verbose:
        print(f"\n✨ Modulization complete!")
        print(f"   Original:    {original_size:.1f} KB")
        print(f"   Index size:  {index_size:.1f} KB")
        print(f"   Token savings: ~{savings:.0f}% (agent reads index first)")
        print(f"\n   Modules written to: {output_path}/")
    
    return {
        "status": "success",
        "original_size_kb": round(original_size, 2),
        "index_size_kb": round(index_size, 2),
        "token_savings_percent": round(savings, 1),
        "output_dir": str(output_path),
        "stats": stats,
    }


def auto_modulize(
    workspace: str = ".",
    threshold_kb: float = 50.0,
    **kwargs
) -> List[dict]:
    """
    Auto-detect and modulize large markdown files in a workspace.
    
    Args:
        workspace: Directory to scan
        threshold_kb: Minimum file size to consider for modulization
        **kwargs: Additional arguments passed to modulize()
        
    Returns:
        List of results for each processed file
    """
    workspace_path = Path(workspace)
    results = []
    
    # Find large markdown files
    for md_file in workspace_path.glob("*.md"):
        size_kb = md_file.stat().st_size / 1024
        if size_kb >= threshold_kb:
            print(f"\n📄 Found large file: {md_file.name} ({size_kb:.1f} KB)")
            
            # Skip if already modulized
            modules_dir = md_file.parent / "modules"
            if (modules_dir / "INDEX.md").exists():
                print(f"   ⏭️  Already modulized, skipping")
                continue
            
            result = modulize(str(md_file), **kwargs)
            results.append(result)
    
    return results
