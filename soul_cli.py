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
    else:
        print(f"Unknown command: {args[0]}")
        print("Usage: soul [init|chat|status]")
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


if __name__ == "__main__":
    main()
