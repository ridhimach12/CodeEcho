import numpy as np
import pytest
from backend.app.embeddings.tfidf_embedder import TFIDFEmbedder

def test_tfidf_dimension_consistency():
    embedder = TFIDFEmbedder(max_features=64)
    texts = [
        "[-] VAR_1 = calc ( ) [+] try : VAR_1 = calc ( ) except Exception : pass",
        "[-] return None [+] if VAR_1 is None : raise ValueError ( )",
    ]
    vectors = embedder.embed(texts)
    assert vectors.shape == (2, embedder.dimension)
    assert vectors.dtype == np.float32

def test_tfidf_empty_inputs_handling():
    embedder = TFIDFEmbedder(max_features=64)
    empty_cases = ["", "   ", "\n\t\n"]
    vectors = embedder.embed(empty_cases)
    assert vectors.shape == (3, embedder.dimension)
    # Norm of all empty input vectors should be 0.0
    for vec in vectors:
        assert np.linalg.norm(vec) == 0.0

def test_tfidf_embed_single_consistency():
    embedder = TFIDFEmbedder(max_features=64)
    text = "[-] if VAR_1 : pass [+] if VAR_1 is not None : return VAR_1"
    v_single = embedder.embed_single(text)
    v_batch = embedder.embed([text])[0]
    assert np.allclose(v_single, v_batch)

def test_cosine_similarity_properties():
    embedder = TFIDFEmbedder(max_features=64)
    t1 = "[-] return x [+] if x is None : raise ValueError ( )"
    t2 = "[-] return y [+] if y is None : raise ValueError ( )"
    t_diff = "[-] for i in range ( 10 ) : print ( i ) [+] while True : break"

    v1 = embedder.embed_single(t1)
    v2 = embedder.embed_single(t2)
    v_diff = embedder.embed_single(t_diff)
    v_zero = np.zeros(embedder.dimension, dtype=np.float32)

    # Identical or near-identical normalized changes should have high similarity
    sim_similar = embedder.cosine_similarity(v1, v2)
    sim_different = embedder.cosine_similarity(v1, v_diff)
    assert sim_similar > sim_different
    assert sim_similar > 0.7

    # Cosine similarity with zero vector should be 0.0 without divide by zero warning
    sim_zero = embedder.cosine_similarity(v1, v_zero)
    assert sim_zero == 0.0

def test_pairwise_cosine_similarity():
    embedder = TFIDFEmbedder(max_features=64)
    texts = [
        "[-] x = None [+] if x is None : raise ValueError ( )",
        "[-] y = 1 [+] y = 2",
    ]
    vecs = embedder.embed(texts)
    matrix = embedder.pairwise_cosine_similarity(vecs)
    assert matrix.shape == (2, 2)
    assert np.isclose(matrix[0, 0], 1.0)
    assert np.isclose(matrix[1, 1], 1.0)
    assert np.isclose(matrix[0, 1], matrix[1, 0])  # Symmetric
