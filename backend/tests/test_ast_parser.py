import pytest
from backend.app.feature_extraction.ast_parser import PythonASTParser, FEATURE_NAMES

def test_ast_extract_exception_handling():
    code = (
        "try:\n"
        "    result = parse_data(raw)\n"
        "except (ValueError, KeyError) as err:\n"
        "    raise RuntimeError('failed')\n"
    )
    features = PythonASTParser.extract_features(code)
    assert features.try_count == 1
    assert features.except_count == 1
    assert features.raise_count == 1
    assert "ValueError" in features.exception_types or "KeyError" in features.exception_types
    assert features.has_syntax_error is False

def test_ast_extract_none_checks_and_conditionals():
    code = (
        "if obj is None:\n"
        "    return 0\n"
        "elif not obj.is_valid():\n"
        "    return -1\n"
        "return obj.value if obj.ready else None\n"
    )
    features = PythonASTParser.extract_features(code)
    assert features.none_check_count >= 1
    assert features.if_count >= 2
    assert features.return_count >= 2
    assert features.has_syntax_error is False

def test_ast_syntax_error_resilience():
    # Fragment with invalid indentation and missing colon
    fragment = "if x > 10\n    return foo(x,\n    unclosed bracket"
    features = PythonASTParser.extract_features(fragment)
    # Should not throw exception, should return valid feature vector
    vec = features.to_vector()
    assert len(vec) == len(FEATURE_NAMES)
    assert features.has_syntax_error is True

def test_ast_empty_input():
    features = PythonASTParser.extract_features("")
    vec = features.to_vector()
    assert len(vec) == len(FEATURE_NAMES)
    assert all(v == 0.0 for v in vec)
    assert features.has_syntax_error is False

def test_ast_analyze_change_shifts():
    deleted = "return data['id']"
    added = (
        "if data is None:\n"
        "    raise KeyError('data missing')\n"
        "try:\n"
        "    return data['id']\n"
        "except Exception:\n"
        "    return None\n"
    )
    profile = PythonASTParser.analyze_change(deleted, added)
    assert len(profile.delta_vector) == len(FEATURE_NAMES)
    assert "added_none_guard" in profile.detected_shifts
    assert "added_exception_handling" in profile.detected_shifts
    assert "added_explicit_raise" in profile.detected_shifts
    assert profile.parsed_successfully is True
