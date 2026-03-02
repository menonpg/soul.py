"""
Unit tests for soul.py v0.1
Run: pytest tests/
All tests mock the LLM client — no API key or SDK required.
"""
import os, sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure soul.py is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def make_agent(tmp_path, provider="anthropic"):
    """Create an Agent with mocked LLM client."""
    import soul as soul_mod
    soul_mod_real_build = soul_mod.Agent._build_client
    soul_mod.Agent._build_client = lambda self: MagicMock()
    agent = soul_mod.Agent(
        soul_path=str(tmp_path / "SOUL.md"),
        memory_path=str(tmp_path / "MEMORY.md"),
        provider=provider,
    )
    soul_mod.Agent._build_client = soul_mod_real_build
    return agent


def test_files_created_on_init(tmp_path):
    agent = make_agent(tmp_path)
    assert (tmp_path / "SOUL.md").exists()
    assert (tmp_path / "MEMORY.md").exists()


def test_memory_appended_after_ask(tmp_path):
    agent = make_agent(tmp_path)
    agent._call = MagicMock(return_value="I remember you, Prahlad.")
    agent.ask("My name is Prahlad.")
    memory = (tmp_path / "MEMORY.md").read_text()
    assert "Prahlad" in memory


def test_memory_persists_across_instances(tmp_path):
    """Core promise: new instance reads memory written by previous instance."""
    import soul as soul_mod
    soul_mod.Agent._build_client = lambda self: MagicMock()

    soul = str(tmp_path / "SOUL.md")
    mem  = str(tmp_path / "MEMORY.md")

    a1 = soul_mod.Agent(soul_path=soul, memory_path=mem)
    a1._call = MagicMock(return_value="Nice to meet you, Prahlad.")
    a1.ask("My name is Prahlad.")

    a2 = soul_mod.Agent(soul_path=soul, memory_path=mem)
    assert "Prahlad" in a2._read_memory()


def test_remember_false_skips_write(tmp_path):
    agent = make_agent(tmp_path)
    agent._call = MagicMock(return_value="OK")
    original = (tmp_path / "MEMORY.md").read_text()
    agent.ask("Don't remember this.", remember=False)
    assert (tmp_path / "MEMORY.md").read_text() == original


def test_manual_remember(tmp_path):
    agent = make_agent(tmp_path)
    agent.remember("I enjoy flying Cessnas.")
    assert "Cessna" in (tmp_path / "MEMORY.md").read_text()


def test_memory_truncation(tmp_path):
    agent = make_agent(tmp_path)
    (tmp_path / "MEMORY.md").write_text("x" * 10000)
    result = agent._read_memory()
    assert len(result) < 10000
    assert "truncated" in result


def test_reset_conversation(tmp_path):
    agent = make_agent(tmp_path)
    agent._history = [{"role": "user", "content": "hello"}]
    agent.reset_conversation()
    assert agent._history == []


def test_invalid_provider(tmp_path):
    import soul as soul_mod
    with pytest.raises(ValueError, match="Unknown provider"):
        soul_mod.Agent._build_client = lambda self: (_ for _ in ()).throw(ValueError("Unknown provider: 'fakeprovider'"))
        agent = make_agent(tmp_path, provider="fakeprovider")
        agent._build_client()


# ── CLI tests ─────────────────────────────────────────────────────────────────

def test_soul_init_creates_files(tmp_path, monkeypatch):
    """soul init creates SOUL.md and MEMORY.md."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "")
    from soul_cli import _init
    _init()
    assert (tmp_path / "SOUL.md").exists()
    assert (tmp_path / "MEMORY.md").exists()

def test_soul_status_no_files(tmp_path, monkeypatch, capsys):
    """soul status shows missing files."""
    monkeypatch.chdir(tmp_path)
    from soul_cli import _status
    _status()
    out = capsys.readouterr().out
    assert "not found" in out

def test_soul_status_with_files(tmp_path, monkeypatch, capsys):
    """soul status shows file stats."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "SOUL.md").write_text("# SOUL\nYou are a test agent.\n")
    (tmp_path / "MEMORY.md").write_text("# MEMORY\n\n## Entry 1\nTest\n")
    from soul_cli import _status
    _status()
    out = capsys.readouterr().out
    assert "SOUL.md" in out
    assert "MEMORY.md" in out

def test_soul_chat_missing_files(tmp_path, monkeypatch):
    """soul chat exits if files missing."""
    monkeypatch.chdir(tmp_path)
    import pytest
    from soul_cli import _chat
    with pytest.raises(SystemExit):
        _chat([])
