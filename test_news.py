"""Tests for NewsSkill: RSS headline parsing and the DuckDuckGo fallback
used when the configured feed is unreachable or unparseable."""

import urllib.error
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from zeno.skills.news import NewsSkill
from zeno.nlu.entity import Entities, extract_entities
from zeno.core.context import Context


_RSS_SAMPLE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Headline One</title></item>
<item><title>Headline Two</title></item>
<item><title>Headline Three</title></item>
<item><title>Headline Four</title></item>
</channel></rss>"""

_ATOM_SAMPLE = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom Headline One</title></entry>
<entry><title>Atom Headline Two</title></entry>
</feed>"""


def _entities(text="what's the news"):
    return extract_entities(text)


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._data


def test_parses_rss_headlines_and_caps_at_three():
    skill = NewsSkill()
    with patch("urllib.request.urlopen", return_value=_FakeResponse(_RSS_SAMPLE)):
        result = skill.handle("news_query", _entities(), Context())
    assert "Headline One" in result
    assert "Headline Three" in result
    assert "Headline Four" not in result  # capped at _MAX_HEADLINES = 3


def test_parses_atom_feed_when_rss_items_absent():
    skill = NewsSkill()
    with patch("urllib.request.urlopen", return_value=_FakeResponse(_ATOM_SAMPLE)):
        result = skill.handle("news_query", _entities(), Context())
    assert "Atom Headline One" in result


def test_falls_back_to_duckduckgo_on_parse_error():
    skill = NewsSkill()
    with patch("urllib.request.urlopen", return_value=_FakeResponse(b"not xml at all <<<")), \
         patch("zeno.skills.search._ddg_query", return_value={"AbstractText": "Fallback news summary"}):
        result = skill.handle("news_query", _entities(), Context())
    assert "Fallback news summary" in result


def test_falls_back_to_duckduckgo_on_url_error():
    skill = NewsSkill()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")), \
         patch("zeno.skills.search._ddg_query", return_value={"Answer": "DDG saved the day"}):
        result = skill.handle("news_query", _entities(), Context())
    assert "DDG saved the day" in result


def test_honest_failure_when_rss_and_fallback_both_fail():
    skill = NewsSkill()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")), \
         patch("zeno.skills.search._ddg_query", return_value=None):
        result = skill.handle("news_query", _entities(), Context())
    assert "can't reach" in result.lower()


def test_empty_feed_reports_no_headlines_without_crashing():
    skill = NewsSkill()
    empty_rss = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    with patch("urllib.request.urlopen", return_value=_FakeResponse(empty_rss)):
        result = skill.handle("news_query", _entities(), Context())
    assert isinstance(result, str) and result
