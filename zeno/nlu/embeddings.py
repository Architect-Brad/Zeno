"""
Zeno NLU — optional semantic embedding layer

The classifier in zeno/nlu/intent.py matches phrasing directly against
trained example phrases (character+word n-grams, k-NN cosine similarity).
That's fast, tiny (no ML framework), and works fully offline out of the
box — but it doesn't generalize semantically. A paraphrase with little
character/word overlap with any training example can miss even though a
human would obviously understand it.

This module is a strictly optional add-on: a small (~90MB, quantized)
sentence-embedding model run locally via ONNX Runtime. It is NOT wired
in to replace the n-gram classifier — zeno/nlu/intent.py only consults
it as a tie-breaker when the n-gram classifier's own confidence is low,
and only overrides the n-gram result when the semantic match clearly
disagrees and scores well. If this module (or its model) isn't
installed, everything falls back to exactly the current behavior.

Requires: pip install onnxruntime tokenizers  (both pure-CPU, no torch,
no transformers). Model: Xenova/all-MiniLM-L6-v2 (a standard, widely
used ONNX export of sentence-transformers/all-MiniLM-L6-v2).
"""

from pathlib import Path

try:
    import onnxruntime as _ort
except ImportError:
    _ort = None

try:
    from tokenizers import Tokenizer as _Tokenizer
except ImportError:
    _Tokenizer = None

_MODEL_DIR = Path.home() / ".zeno" / "embeddings"
_MODEL_URL = "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model_quantized.onnx"
_TOKENIZER_URL = "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/tokenizer.json"

_session = None
_tokenizer = None
_intent_centroids = None  # dict[str, np.ndarray], built lazily on first use

# Below this n-gram classifier confidence, it's worth asking the
# embedding model for a second opinion. Above it, the n-gram result is
# almost always fine and we skip the (much slower) embedding inference.
LOW_CONFIDENCE_THRESHOLD = 0.55
# The semantic match must beat the n-gram result by at least this much
# to override it — a slim margin isn't worth surprising the user with a
# different answer than usual.
OVERRIDE_MARGIN = 0.12


def _model_path() -> Path:
    return _MODEL_DIR / "model_quantized.onnx"


def _tokenizer_path() -> Path:
    return _MODEL_DIR / "tokenizer.json"


def is_available() -> bool:
    return _ort is not None and _Tokenizer is not None


def is_model_downloaded() -> bool:
    return _model_path().exists() and _tokenizer_path().exists()


def download_model() -> bool:
    """Download the embedding model + tokenizer if not already present."""
    if is_model_downloaded():
        return True
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        for url, path in ((_MODEL_URL, _model_path()), (_TOKENIZER_URL, _tokenizer_path())):
            print(f"[Zeno] Downloading NLU embedding file ({url})...")
            urllib.request.urlretrieve(url, str(path))
        return is_model_downloaded()
    except Exception as e:
        print(f"[Zeno] Failed to download embedding model: {e}")
        for path in (_model_path(), _tokenizer_path()):
            if path.exists():
                path.unlink()
        return False


def _get_session():
    global _session
    if _session is None:
        _session = _ort.InferenceSession(str(_model_path()), providers=["CPUExecutionProvider"])
    return _session


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = _Tokenizer.from_file(str(_tokenizer_path()))
    return _tokenizer


def embed(text: str):
    """Return a single L2-normalized sentence embedding (np.ndarray) for
    `text`, or None if the engine isn't ready or inference fails."""
    if not is_available() or not is_model_downloaded():
        return None
    try:
        import numpy as np
        session = _get_session()
        tokenizer = _get_tokenizer()
        encoding = tokenizer.encode(text)
        input_ids = np.array([encoding.ids], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

        # Different ONNX exports want different input sets — only feed
        # what this particular model actually declares, rather than
        # assuming a fixed signature.
        wanted = {i.name for i in session.get_inputs()}
        feed = {}
        if "input_ids" in wanted:
            feed["input_ids"] = input_ids
        if "attention_mask" in wanted:
            feed["attention_mask"] = attention_mask
        if "token_type_ids" in wanted:
            feed["token_type_ids"] = np.zeros_like(input_ids)

        outputs = session.run(None, feed)
        token_embeddings = outputs[0][0]  # (seq_len, hidden_size)
        mask = attention_mask[0].astype(np.float32)[:, None]
        summed = (token_embeddings * mask).sum(axis=0)
        counts = np.clip(mask.sum(axis=0), 1e-9, None)
        pooled = summed / counts  # mean pooling over real (non-padding) tokens
        norm = np.linalg.norm(pooled)
        return pooled / norm if norm > 0 else pooled
    except Exception as e:
        print(f"[Zeno] Embedding error: {e}")
        return None


def cosine_similarity(a, b) -> float:
    import numpy as np
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _build_intent_centroids(training_data: dict) -> dict:
    """Average embedding of each intent's training phrases — a cheap
    representative vector used for semantic similarity comparison.
    Capped per intent so first-load stays reasonably fast."""
    import numpy as np
    centroids = {}
    for intent, phrases in training_data.items():
        vectors = [embed(p) for p in phrases[:15]]
        vectors = [v for v in vectors if v is not None]
        if vectors:
            centroid = np.mean(vectors, axis=0)
            norm = np.linalg.norm(centroid)
            centroids[intent] = centroid / norm if norm > 0 else centroid
    return centroids


def get_intent_centroids(training_data: dict) -> dict:
    """Lazily build and cache per-intent centroid embeddings. Call
    reset_centroids() if training_data changes at runtime (e.g. tests)."""
    global _intent_centroids
    if _intent_centroids is None:
        _intent_centroids = _build_intent_centroids(training_data)
    return _intent_centroids


def reset_centroids():
    global _intent_centroids
    _intent_centroids = None


def best_semantic_match(text: str, training_data: dict):
    """Return (intent, similarity) for the training intent whose centroid
    is closest to `text`, or None if embeddings aren't available/ready."""
    query = embed(text)
    if query is None:
        return None
    centroids = get_intent_centroids(training_data)
    if not centroids:
        return None
    best_intent, best_score = None, -1.0
    for intent, centroid in centroids.items():
        score = cosine_similarity(query, centroid)
        if score > best_score:
            best_intent, best_score = intent, score
    return (best_intent, best_score) if best_intent is not None else None
