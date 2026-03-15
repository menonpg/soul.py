"""soul CLI — init, chat, status commands."""
import sys, os
from pathlib import Path


def main():
    args = sys.argv[1:]
    if not args or args[0] == "init":
        _init()
    elif args[0] == "chat":
        _chat(args[1:])
    elif args[0] == "status":
        _status()
    elif args[0] == "modulize":
        _modulize(args[1:])
    elif args[0] == "modules":
        _modules(args[1:])
    else:
        print(f"Unknown command: {args[0]}")
        print("Usage: soul [init|chat|status|modulize|modules]")
        sys.exit(1)


def _init():
    print("\n🧠 soul.py setup\n")
    name     = input("Agent name [Assistant]: ").strip() or "Assistant"
    provider = input("LLM provider — anthropic / openai / openai-compatible [anthropic]: ").strip() or "anthropic"

    soul_content = (
        f"# SOUL.md\nYou are {name}.\n"
        "You have a persistent memory and strong opinions.\n"
        "You are concise, direct, and genuinely helpful.\n"
    )
    mem_content = "# MEMORY.md\n(No memories yet.)\n"

    with open("SOUL.md", "w") as f: f.write(soul_content)
    with open("MEMORY.md", "w") as f: f.write(mem_content)

    print(f"\n✅ Created SOUL.md and MEMORY.md")
    print(f"   Provider: {provider}")
    if provider == "anthropic":
        print("\n   export ANTHROPIC_API_KEY=sk-ant-...")
        print("   pip install soul-agent[anthropic]")
    elif provider == "openai":
        print("\n   export OPENAI_API_KEY=sk-...")
        print("   pip install soul-agent[openai]")
    else:
        print("\n   soul chat --base-url http://localhost:11434/v1 --provider openai-compatible")
    print("\n   Then: soul chat")


def _chat(args):
    """Interactive REPL with persistent memory."""
    provider  = "anthropic"
    model     = None
    base_url  = None
    soul_path = "SOUL.md"
    mem_path  = "MEMORY.md"
    mode      = "auto"

    i = 0
    while i < len(args):
        if   args[i] == "--provider"  and i+1 < len(args): provider  = args[i+1]; i+=2
        elif args[i] == "--model"     and i+1 < len(args): model     = args[i+1]; i+=2
        elif args[i] == "--base-url"  and i+1 < len(args): base_url  = args[i+1]; i+=2
        elif args[i] == "--soul"      and i+1 < len(args): soul_path = args[i+1]; i+=2
        elif args[i] == "--memory"    and i+1 < len(args): mem_path  = args[i+1]; i+=2
        elif args[i] == "--mode"      and i+1 < len(args): mode      = args[i+1]; i+=2
        else: i+=1

    if not Path(soul_path).exists() or not Path(mem_path).exists():
        print("⚠️  SOUL.md or MEMORY.md not found. Run: soul init")
        sys.exit(1)

    # Use HybridAgent if env configured, fall back to simple Agent
    # If --base-url is set (Ollama/local), skip HybridAgent and go straight to Agent
    agent = None
    agent_type = None

    if not base_url:
        try:
            from hybrid_agent import HybridAgent
            agent = HybridAgent(soul_path=soul_path, memory_path=mem_path, mode=mode)
            agent_type = "v2.0 (RAG+RLM)"
        except Exception:
            pass

    if agent is None:
        try:
            from soul import Agent
            agent = Agent(soul_path=soul_path, memory_path=mem_path,
                          provider=provider, model=model, base_url=base_url)
            agent_type = "v0.1 (markdown)"
        except Exception as e:
            print(f"\n⚠️  Could not initialize agent: {e}")
            print("\nFor Ollama, make sure to pass --provider and --base-url:")
            print("  soul chat --provider openai-compatible --base-url http://localhost:11434/v1 --model llama3.2")
            print("\nFor Anthropic:  export ANTHROPIC_API_KEY=sk-ant-...")
            print("For OpenAI:     export OPENAI_API_KEY=sk-...")
            sys.exit(1)

    mem_lines = Path(mem_path).read_text().count("\n## ")
    print(f"\n🧠 soul.py {agent_type}")
    print(f"   Soul:   {soul_path}")
    print(f"   Memory: {mem_path} ({mem_lines} entries)")
    print(f"   Commands: /memory  /reset  /help  exit\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input: continue
            if user_input.lower() in ("exit","quit","bye","/exit","/quit"):
                print("\n👋 Memory saved. See you next time.")
                break
            if user_input.lower() in ("/memory","/mem"):
                print("\n" + Path(mem_path).read_text() + "\n"); continue
            if user_input.lower() == "/reset":
                agent.reset_conversation()
                print("↺ Conversation reset (memory preserved)\n"); continue
            if user_input.lower() == "/help":
                print("\nCommands:\n  /memory  — show full MEMORY.md\n  /reset   — clear conversation history\n  /help    — this message\n  exit     — quit\n"); continue
            try:
                result = agent.ask(user_input)
                if isinstance(result, dict):
                    answer = result["answer"]
                    route  = result.get("route","")
                    ms     = result.get("total_ms","")
                    suffix = f"  \033[2m[{route} · {ms}ms]\033[0m" if route else ""
                    print(f"\nAssistant: {answer}{suffix}\n")
                else:
                    print(f"\nAssistant: {result}\n")
            except Exception as e:
                print(f"\n⚠️  Error: {e}\n")
    except KeyboardInterrupt:
        print("\n\n👋 Memory saved. See you next time.")


def _status():
    """Show memory stats for current directory."""
    print("\n🧠 soul.py status\n")
    soul_path = Path("SOUL.md")
    mem_path  = Path("MEMORY.md")

    if soul_path.exists():
        print(f"✅ SOUL.md     — {len(soul_path.read_text().splitlines())} lines")
    else:
        print("❌ SOUL.md     — not found (run: soul init)")

    if mem_path.exists():
        content = mem_path.read_text()
        entries = content.count("\n## ")
        size    = len(content.encode())
        print(f"✅ MEMORY.md   — {entries} entries, {size/1024:.1f}KB")
    else:
        print("❌ MEMORY.md   — not found (run: soul init)")
    print()


def _modulize(args):
    """Modulize a large markdown file into indexed modules."""
    from modulizer import modulize, auto_modulize
    
    # Parse args
    input_file = None
    output_dir = None
    provider = "anthropic"
    model = None
    base_url = None
    dry_run = False
    auto = False
    threshold = 50.0
    
    i = 0
    while i < len(args):
        if args[i] == "--auto":
            auto = True; i += 1
        elif args[i] == "--output" and i+1 < len(args):
            output_dir = args[i+1]; i += 2
        elif args[i] == "--provider" and i+1 < len(args):
            provider = args[i+1]; i += 2
        elif args[i] == "--model" and i+1 < len(args):
            model = args[i+1]; i += 2
        elif args[i] == "--base-url" and i+1 < len(args):
            base_url = args[i+1]; i += 2
        elif args[i] == "--dry-run":
            dry_run = True; i += 1
        elif args[i] == "--threshold" and i+1 < len(args):
            threshold = float(args[i+1]); i += 2
        elif not args[i].startswith("-"):
            input_file = args[i]; i += 1
        else:
            i += 1
    
    if auto:
        results = auto_modulize(
            threshold_kb=threshold,
            provider=provider,
            model=model,
            base_url=base_url,
            dry_run=dry_run,
        )
        if not results:
            print(f"\nNo files above {threshold}KB found.")
        return
    
    if not input_file:
        input_file = "MEMORY.md"
    
    if not Path(input_file).exists():
        print(f"⚠️  File not found: {input_file}")
        print("Usage: soul modulize <file.md> [--output dir] [--provider anthropic|openai|gemini]")
        print("       soul modulize --auto [--threshold 50]")
        sys.exit(1)
    
    modulize(
        input_file,
        output_dir=output_dir,
        provider=provider,
        model=model,
        base_url=base_url,
        dry_run=dry_run,
    )


def _modules(args):
    """Manage modules."""
    if not args or args[0] == "list":
        _modules_list()
    elif args[0] == "reindex":
        _modules_reindex(args[1:])
    else:
        print(f"Unknown subcommand: {args[0]}")
        print("Usage: soul modules [list|reindex]")
        sys.exit(1)


def _modules_list():
    """List current modules."""
    modules_dir = Path("modules")
    if not modules_dir.exists():
        print("\n⚠️  No modules directory found.")
        print("   Run: soul modulize MEMORY.md")
        return
    
    print("\n🧠 soul.py modules\n")
    
    index_path = modules_dir / "INDEX.md"
    if index_path.exists():
        print(f"📑 INDEX.md — {len(index_path.read_text().encode())/1024:.1f}KB")
    
    total_size = 0
    for md_file in sorted(modules_dir.glob("*.md")):
        if md_file.name == "INDEX.md":
            continue
        size = len(md_file.read_text().encode()) / 1024
        total_size += size
        print(f"   📄 {md_file.name} — {size:.1f}KB")
    
    print(f"\n   Total: {total_size:.1f}KB across {len(list(modules_dir.glob('*.md')))-1} modules")
    print()


def _modules_reindex(args):
    """Regenerate INDEX.md from existing modules."""
    from modulizer.indexer import generate_index
    from modulizer.splitter import Module
    from modulizer.classifier import ClassifiedChunk
    from modulizer.chunker import Chunk
    
    modules_dir = Path("modules")
    if not modules_dir.exists():
        print("⚠️  No modules directory found.")
        return
    
    provider = "anthropic"
    for i, arg in enumerate(args):
        if arg == "--provider" and i+1 < len(args):
            provider = args[i+1]
    
    # Load existing modules
    modules = []
    for md_file in sorted(modules_dir.glob("*.md")):
        if md_file.name == "INDEX.md":
            continue
        
        content = md_file.read_text()
        category = md_file.stem.split("-")[0]  # Handle "projects-1.md" -> "projects"
        
        # Create a simple module representation
        chunk = Chunk(
            header=category.title(),
            level=1,
            content=content,
            line_start=0,
            line_end=content.count("\n")
        )
        classified = ClassifiedChunk(
            chunk=chunk,
            category=category,
            confidence=1.0,
            keywords=[]
        )
        modules.append(Module(
            name=md_file.name,
            category=category,
            chunks=[classified]
        ))
    
    print(f"\n🔄 Regenerating INDEX.md from {len(modules)} modules...")
    
    index_content = generate_index(
        modules,
        original_file="(existing modules)",
        provider=provider,
        include_summaries=True,
    )
    
    (modules_dir / "INDEX.md").write_text(index_content)
    print("✓ INDEX.md updated")
    print()


if __name__ == "__main__":
    main()
