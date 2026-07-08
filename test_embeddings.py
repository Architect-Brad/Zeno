"""Tests for zeno/nlu/embeddings.py — the optional semantic tie-breaker,
and its conservative wiring into classify_intent()."""

import numpy as np
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Availability / download gating
# ---------------------------------------------------------------------------

def test_unavailable_when_onnxruntime_missing():
    with patch("zeno.nlu.embeddings._ort", None):
        from zeno.nlu import embeddings
        assert embeddings.is_available() is False


def test_unavailable_when_tokenizers_missing():
    with patch("zeno.nlu.embeddings._Tokenizer", None):
        from zeno.nlu import embeddings
        assert embeddings.is_available() is False


def test_available_when_both_present():
    with patch("zeno.nlu.embeddings._ort", MagicMock()), \
         patch("zeno.nlu.embeddings._Tokenizer", MagicMock()):
        from zeno.nlu import embeddings
        assert embeddings.is_available() is True


def test_model_downloaded_false_when_files_missing(tmp_path):
    from zeno.nlu import embeddings
    with patch("zeno.nlu.embeddings._MODEL_DIR", tmp_path):
        assert embeddings.is_model_downloaded() is False


def test_model_downloaded_true_when_both_files_present(tmp_path):
    from zeno.nlu import embeddings
    (tmp_path / "model_quantized.onnx").write_bytes(b"fake")
    (tmp_path / "tokenizer.json").write_text("{}")
    with patch("zeno.nlu.embeddings._MODEL_DIR", tmp_path):
        assert embeddings.is_model_downloaded() is True


def test_embed_returns_none_when_not_ready():
    from zeno.nlu import embeddings
    with patch("zeno.nlu.embeddings._ort", None):
        assert embeddings.embed("hello") is None


# ---------------------------------------------------------------------------
# embed() inference plumbing
# ---------------------------------------------------------------------------

def test_embed_only_feeds_inputs_the_session_declares(tmp_path):
    from zeno.nlu import embeddings

    fake_encoding = MagicMock()
    fake_encoding.ids = [1, 2, 3]
    fake_encoding.attention_mask = [1, 1, 1]

    fake_tokenizer = MagicMock()
    fake_tokenizer.encode.return_value = fake_encoding

    fake_session = MagicMock()
    fake_session.get_inputs.return_value = [MagicMock(name="input_ids"), MagicMock(name="attention_mask")]
    for inp, name in zip(fake_session.get_inputs.return_value, ["input_ids", "attention_mask"]):
        inp.name = name
    # hidden_size=4, seq_len=3
    fake_session.run.return_value = [np.ones((1, 3, 4), dtype=np.float32)]

    with patch("zeno.nlu.embeddings._ort", MagicMock()), \
         patch("zeno.nlu.embeddings._Tokenizer", MagicMock()), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings._get_session", return_value=fake_session), \
         patch("zeno.nlu.embeddings._get_tokenizer", return_value=fake_tokenizer):
        result = embeddings.embed("hello there")

    assert result is not None
    fed = fake_session.run.call_args[0][1]
    assert "input_ids" in fed
    assert "attention_mask" in fed
    assert "token_type_ids" not in fed  # session didn't declare it, so we shouldn't feed it
    # L2-normalized
    assert abs(float(np.linalg.norm(result)) - 1.0) < 1e-5


def test_embed_includes_token_type_ids_when_declared(tmp_path):
    from zeno.nlu import embeddings

    fake_encoding = MagicMock()
    fake_encoding.ids = [1, 2]
    fake_encoding.attention_mask = [1, 1]

    fake_tokenizer = MagicMock()
    fake_tokenizer.encode.return_value = fake_encoding

    names = ["input_ids", "attention_mask", "token_type_ids"]
    inputs = []
    for n in names:
        m = MagicMock()
        m.name = n
        inputs.append(m)

    fake_session = MagicMock()
    fake_session.get_inputs.return_value = inputs
    fake_session.run.return_value = [np.ones((1, 2, 4), dtype=np.float32)]

    with patch("zeno.nlu.embeddings._ort", MagicMock()), \
         patch("zeno.nlu.embeddings._Tokenizer", MagicMock()), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings._get_session", return_value=fake_session), \
         patch("zeno.nlu.embeddings._get_tokenizer", return_value=fake_tokenizer):
        embeddings.embed("hi")

    fed = fake_session.run.call_args[0][1]
    assert "token_type_ids" in fed


def test_embed_returns_none_and_does_not_raise_on_inference_error(tmp_path):
    from zeno.nlu import embeddings
    with patch("zeno.nlu.embeddings._ort", MagicMock()), \
         patch("zeno.nlu.embeddings._Tokenizer", MagicMock()), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings._get_session", side_effect=RuntimeError("boom")):
        assert embeddings.embed("hello") is None


# ---------------------------------------------------------------------------
# cosine_similarity / centroids / best_semantic_match
# ---------------------------------------------------------------------------

def test_cosine_similarity_identical_vectors_is_one():
    from zeno.nlu import embeddings
    v = np.array([1.0, 2.0, 3.0])
    assert abs(embeddings.cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors_is_zero():
    from zeno.nlu import embeddings
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(embeddings.cosine_similarity(a, b)) < 1e-9


def test_cosine_similarity_handles_zero_vector():
    from zeno.nlu import embeddings
    a = np.zeros(3)
    b = np.array([1.0, 2.0, 3.0])
    assert embeddings.cosine_similarity(a, b) == 0.0


def test_best_semantic_match_returns_none_when_embed_fails():
    from zeno.nlu import embeddings
    embeddings.reset_centroids()
    with patch("zeno.nlu.embeddings.embed", return_value=None):
        assert embeddings.best_semantic_match("hello", {"greeting": ["hi"]}) is None


def test_best_semantic_match_picks_closest_centroid():
    from zeno.nlu import embeddings
    embeddings.reset_centroids()

    def fake_embed(text):
        # Deterministic toy embeddings: greeting phrases cluster near
        # [1,0]; farewell phrases cluster near [0,1].
        if text in ("hi", "hello", "query"):
            return np.array([1.0, 0.0]) if text != "query" else np.array([0.9, 0.1])
        return np.array([0.0, 1.0])

    with patch("zeno.nlu.embeddings.embed", side_effect=fake_embed):
        result = embeddings.best_semantic_match(
            "query", {"greeting": ["hi", "hello"], "farewell": ["bye", "goodbye"]}
        )
    assert result is not None
    intent, score = result
    assert intent == "greeting"
    assert score > 0.8


def test_get_intent_centroids_is_cached_between_calls():
    from zeno.nlu import embeddings
    embeddings.reset_centroids()
    call_count = {"n": 0}

    def fake_embed(text):
        call_count["n"] += 1
        return np.array([1.0, 0.0])

    with patch("zeno.nlu.embeddings.embed", side_effect=fake_embed):
        embeddings.get_intent_centroids({"greeting": ["hi"]})
        first_count = call_count["n"]
        embeddings.get_intent_centroids({"greeting": ["hi"]})  # should hit cache
        assert call_count["n"] == first_count


# ---------------------------------------------------------------------------
# Conservative wiring into classify_intent()
# ---------------------------------------------------------------------------

def test_classify_intent_unchanged_when_embeddings_module_absent():
    from zeno.nlu.intent import classify_intent
    # No mocking at all — embeddings.py exists but has no model downloaded
    # in this test environment, so classify_intent must behave exactly
    # as it did before this feature existed.
    result = classify_intent("what time is it")
    assert result.intent == "time_query"


def test_classify_intent_keeps_ngram_result_when_confidence_is_high():
    from zeno.nlu import intent as intent_mod
    with patch("zeno.nlu.embeddings.is_available", return_value=True), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings.best_semantic_match") as mock_match:
        result = intent_mod.classify_intent("what time is it")
    # High-confidence n-gram result shouldn't even consult embeddings
    mock_match.assert_not_called()
    assert result.intent == "time_query"


def test_classify_intent_overrides_low_confidence_result_on_strong_semantic_disagreement():
    from zeno.nlu import intent as intent_mod
    from zeno.nlu.intent import IntentResult

    fake_low_confidence = IntentResult(intent="unknown", confidence=0.2, raw="xyz")

    with patch.object(intent_mod, "get_classifier") as mock_get_classifier, \
         patch("zeno.nlu.embeddings.is_available", return_value=True), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings.best_semantic_match", return_value=("joke", 0.9)):
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = fake_low_confidence
        mock_get_classifier.return_value = mock_classifier

        result = intent_mod.classify_intent("make me chuckle")

    assert result.intent == "joke"
    assert result.confidence == 0.9


def test_classify_intent_keeps_ngram_result_when_semantic_margin_too_small():
    from zeno.nlu import intent as intent_mod
    from zeno.nlu.intent import IntentResult

    fake_low_confidence = IntentResult(intent="unknown", confidence=0.4, raw="xyz")

    with patch.object(intent_mod, "get_classifier") as mock_get_classifier, \
         patch("zeno.nlu.embeddings.is_available", return_value=True), \
         patch("zeno.nlu.embeddings.is_model_downloaded", return_value=True), \
         patch("zeno.nlu.embeddings.best_semantic_match", return_value=("joke", 0.45)):
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = fake_low_confidence
        mock_get_classifier.return_value = mock_classifier

        result = intent_mod.classify_intent("make me chuckle")

    # 0.45 - 0.4 = 0.05 margin, below OVERRIDE_MARGIN (0.12) — keep n-gram result
    assert result.intent == "unknown"


def test_classify_intent_swallows_embedding_errors_and_keeps_ngram_result():
    from zeno.nlu import intent as intent_mod
    from zeno.nlu.intent import IntentResult

    fake_low_confidence = IntentResult(intent="unknown", confidence=0.2, raw="xyz")

    with patch.object(intent_mod, "get_classifier") as mock_get_classifier, \
         patch("zeno.nlu.embeddings.is_available", side_effect=RuntimeError("boom")):
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = fake_low_confidence
        mock_get_classifier.return_value = mock_classifier

        result = intent_mod.classify_intent("xyz")

    assert result.intent == "unknown"  # unchanged despite the internal error
