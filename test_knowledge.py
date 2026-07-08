"""Tests for KnowledgeSkill: local knowledge graph lookup first, then a
Wikipedia retrieval fallback (pure retrieval, never generation), with
caching so a repeat question doesn't hit the network again."""

import os
import tempfile
from unittest.mock import patch

import zeno.memory.graph as graph_mod
from zeno.memory.graph import KnowledgeGraph, Entity

from zeno.skills.knowledge import KnowledgeSkill, _trim_summary, _wikipedia_lookup
from zeno.nlu.entity import extract_entities
from zeno.core.context import Context


def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    graph_mod._graph = KnowledgeGraph(path=path)


def _entities(text):
    return extract_entities(text, intent_hint="knowledge_query")


# ---------------------------------------------------------------------------
# _trim_summary
# ---------------------------------------------------------------------------

def test_trim_summary_keeps_first_two_sentences():
    text = "First sentence here. Second sentence here. Third sentence should be cut."
    result = _trim_summary(text)
    assert "First sentence" in result
    assert "Second sentence" in result
    assert "Third sentence" not in result


def test_trim_summary_truncates_long_single_sentence():
    text = "word " * 200 + "."
    result = _trim_summary(text, max_chars=50)
    assert len(result) <= 51  # 50 + ellipsis char
    assert result.endswith("…")


# ---------------------------------------------------------------------------
# _wikipedia_lookup
# ---------------------------------------------------------------------------

def test_wikipedia_lookup_returns_none_when_search_fails():
    with patch("zeno.skills.knowledge._fetch_json", return_value=None):
        assert _wikipedia_lookup("napoleon") is None


def test_wikipedia_lookup_returns_none_when_no_search_hits():
    with patch("zeno.skills.knowledge._fetch_json", return_value={"query": {"search": []}}):
        assert _wikipedia_lookup("asdkjfhaslkdjfh") is None


def test_wikipedia_lookup_returns_none_when_summary_has_no_extract():
    search_result = {"query": {"search": [{"title": "Napoleon"}]}}
    with patch("zeno.skills.knowledge._fetch_json", side_effect=[search_result, {}]):
        assert _wikipedia_lookup("napoleon") is None


def test_wikipedia_lookup_returns_title_and_trimmed_summary():
    search_result = {"query": {"search": [{"title": "Napoleon"}]}}
    summary_result = {"extract": "Napoleon Bonaparte was a French military leader. He was Emperor."}
    with patch("zeno.skills.knowledge._fetch_json", side_effect=[search_result, summary_result]):
        result = _wikipedia_lookup("who was napoleon")
    assert result == ("Napoleon", "Napoleon Bonaparte was a French military leader. He was Emperor.")


# ---------------------------------------------------------------------------
# KnowledgeSkill.handle — local graph first
# ---------------------------------------------------------------------------

def test_handle_uses_local_graph_facts_without_touching_network():
    graph = graph_mod.get_graph()
    graph.add_entity(Entity(name="zeno", type="software"))
    graph.add_triple("zeno", "is_a", "voice assistant")

    skill = KnowledgeSkill()
    with patch("zeno.skills.knowledge._wikipedia_lookup") as mock_wiki:
        result = skill.handle("knowledge_query", _entities("what is zeno"), Context())

    mock_wiki.assert_not_called()
    assert "zeno" in result.lower()
    assert "voice assistant" in result.lower()


def test_handle_uses_cached_wikipedia_summary_without_network():
    graph = graph_mod.get_graph()
    graph.add_entity(Entity(
        name="napoleon", type="topic",
        properties={"summary": "Napoleon was a French leader.", "source": "wikipedia"},
    ))

    skill = KnowledgeSkill()
    with patch("zeno.skills.knowledge._wikipedia_lookup") as mock_wiki:
        result = skill.handle("knowledge_query", _entities("who was napoleon"), Context())

    mock_wiki.assert_not_called()
    assert result == "Napoleon was a French leader."


# ---------------------------------------------------------------------------
# KnowledgeSkill.handle — Wikipedia fallback + caching
# ---------------------------------------------------------------------------

def test_handle_falls_back_to_wikipedia_when_graph_is_empty():
    skill = KnowledgeSkill()
    with patch("zeno.skills.knowledge._wikipedia_lookup",
               return_value=("Napoleon", "Napoleon was a French military leader.")):
        result = skill.handle("knowledge_query", _entities("who was napoleon"), Context())
    assert result == "Napoleon was a French military leader."


def test_handle_caches_wikipedia_result_for_next_time():
    skill = KnowledgeSkill()
    with patch("zeno.skills.knowledge._wikipedia_lookup",
               return_value=("Napoleon", "Napoleon was a French military leader.")):
        skill.handle("knowledge_query", _entities("who was napoleon"), Context())

    # Second call should hit the now-cached entity, not the network
    with patch("zeno.skills.knowledge._wikipedia_lookup") as mock_wiki:
        result = skill.handle("knowledge_query", _entities("who was napoleon"), Context())
    mock_wiki.assert_not_called()
    assert result == "Napoleon was a French military leader."


def test_handle_honest_when_both_local_and_wikipedia_miss():
    skill = KnowledgeSkill()
    with patch("zeno.skills.knowledge._wikipedia_lookup", return_value=None):
        result = skill.handle("knowledge_query", _entities("who was zzqxnotarealperson"), Context())
    assert "don't know" in result.lower()
    assert "couldn't find" in result.lower()


def test_handle_no_subject_gives_helpful_prompt_without_network():
    skill = KnowledgeSkill()
    entities = _entities("tell me about")  # empty subject after prefix strip
    with patch("zeno.skills.knowledge._wikipedia_lookup") as mock_wiki:
        result = skill.handle("knowledge_query", entities, Context())
    mock_wiki.assert_not_called()
    assert "knowledge base" in result.lower()


def test_extract_subject_handles_various_prefixes():
    skill = KnowledgeSkill()
    assert skill._extract_subject("what is gravity", _entities("what is gravity")) == "gravity"
    assert skill._extract_subject("who was napoleon", _entities("who was napoleon")) == "napoleon"
    assert skill._extract_subject("tell me about mars", _entities("tell me about mars")) == "mars"
