import pytest
from backend.app.repository_mining.validator import validate_github_url, RepoValidationError

def test_valid_github_urls():
    valid_cases = [
        ("https://github.com/pallets/flask", "pallets", "flask"),
        ("https://github.com/psf/requests.git", "psf", "requests"),
        ("https://www.github.com/python/cpython/", "python", "cpython"),
        ("https://github.com/scikit-learn/scikit-learn", "scikit-learn", "scikit-learn"),
    ]
    for url, expected_owner, expected_repo in valid_cases:
        res = validate_github_url(url)
        assert res["owner"] == expected_owner
        assert res["repo"] == expected_repo
        assert res["normalized_url"].startswith("https://github.com/")

def test_invalid_github_urls():
    invalid_cases = [
        "http://github.com/pallets/flask",       # Insecure HTTP
        "https://gitlab.com/owner/repo",        # Non-github
        "https://evil.com/fake/repo",           # Malicious host
        "https://github.com/owner/repo; rm -rf",# Shell injection attempt
        "https://github.com/owner/repo`whoami`", # Command interpolation
        "ftp://github.com/owner/repo",          # Invalid protocol
        "",                                     # Empty string
        "not-a-url",                            # Malformed
    ]
    for bad_url in invalid_cases:
        with pytest.raises(RepoValidationError):
            validate_github_url(bad_url)
