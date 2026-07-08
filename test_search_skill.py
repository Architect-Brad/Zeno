"""Tests for SearchSkill: define_word, translate_phrase, find_place."""

from unittest.mock import patch

from zeno.skills.search import SearchSkill
from zeno.nlu.entity import extract_entities
from zeno.core.context import Context


def _entities(text):
    return extract_entities(text)


def test_news_query_is_not_claimed_by_search_skill():
    # Regression guard for the bug where SearchSkill silently shadowed
    # NewsSkill's real RSS implementation because it was registered later.
    assert "news_query" not in SearchSkill.intents


def test_define_word_uses_dictionary_api_first():
    skill = SearchSkill()
    with patch("zeno.skills.search._dict_definition", return_value="a small furry mammal"):
        result = skill.handle("define_word", _entities("define cat"), Context())
    assert "cat" in result.lower()
    assert "furry mammal" in result.lower()


def test_define_word_falls_back_to_ddg_when_dictionary_empty():
    skill = SearchSkill()
    with patch("zeno.skills.search._dict_definition", return_value=None), \
         patch("zeno.skills.search._ddg_query", return_value={"AbstractText": "a ddg definition"}):
        result = skill.handle("define_word", _entities("define zorbnax"), Context())
    assert "ddg definition" in result.lower()


def test_define_word_no_result_when_both_fail():
    skill = SearchSkill()
    with patch("zeno.skills.search._dict_definition", return_value=None), \
         patch("zeno.skills.search._ddg_query", return_value=None):
        result = skill.handle("define_word", _entities("define zorbnax"), Context())
    assert isinstance(result, str) and result


def test_translate_phrase_uses_ddg():
    skill = SearchSkill()
    with patch("zeno.skills.search._ddg_query", return_value={"Answer": "hola"}):
        result = skill.handle("translate_phrase", _entities("translate hello to spanish"), Context())
    assert "hola" in result.lower()


def test_find_place_uses_ddg():
    skill = SearchSkill()
    with patch("zeno.skills.search._ddg_query",
               return_value={"AbstractText": "A well-known coffee shop chain"}):
        result = skill.handle("find_place", _entities("find starbucks nearby"), Context())
    assert "coffee shop" in result.lower()


def test_find_place_empty_query_does_not_crash():
    skill = SearchSkill()
    entities = _entities("find")
    entities.raw["text"] = ""
    result = skill.handle("find_place", entities, Context())
    assert isinstance(result, str) and result
