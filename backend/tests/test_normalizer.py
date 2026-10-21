from backend.app.repository_mining.normalizer import (
    strip_comments_and_docstrings,
    canonicalize_identifiers,
    normalize_code_diff,
)

def test_strip_comments():
    code = (
        "def compute(x):\n"
        "    # Calculate square\n"
        "    result = x * x # inline comment\n"
        "    return result\n"
    )
    cleaned = strip_comments_and_docstrings(code)
    assert "# Calculate square" not in cleaned
    assert "# inline comment" not in cleaned
    assert "compute" in cleaned
    assert "result" in cleaned

def test_canonicalize_identifiers():
    code = "user_input = 42\nresult_val = user_input * 2\nreturn result_val"
    canonical = canonicalize_identifiers(code)
    # Variable names should be replaced with VAR_1, VAR_2
    assert "user_input" not in canonical
    assert "result_val" not in canonical
    assert "VAR_1" in canonical
    assert "VAR_2" in canonical
    assert "return" in canonical  # keyword preserved

def test_normalize_code_diff():
    old = "x = calc_old(a)"
    new = "y = calc_new(b)"
    normalized = normalize_code_diff(added_code=new, deleted_code=old)
    assert "[-]" in normalized
    assert "[+]" in normalized
