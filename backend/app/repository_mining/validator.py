import re
from urllib.parse import urlparse

# Pattern to strictly match public GitHub repository URLs
# Examples:
#   https://github.com/pallets/flask
#   https://github.com/psf/requests.git
GITHUB_URL_REGEX = re.compile(
    r"^https://(?:www\.)?github\.com/(?P<owner>[a-zA-Z0-9_\-\.]+)/(?P<repo>[a-zA-Z0-9_\-\.]+?)(?:\.git)?/?$"
)

# Unsafe shell/path characters that should never be in repo strings
FORBIDDEN_CHARS = {";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", "\\", " "}

class RepoValidationError(ValueError):
    """Raised when repository URL or inputs fail validation."""
    pass

def validate_github_url(url: str) -> dict[str, str]:
    """
    Validates that the provided URL is a secure, well-formed GitHub repository URL.
    Mitigates SSRF, protocol injection (only HTTPS allowed), and path traversal.
    
    Returns:
        dict with 'owner', 'repo', 'normalized_url'
    """
    if not url or not isinstance(url, str):
        raise RepoValidationError("Repository URL must be a non-empty string.")
        
    url = url.strip()
    
    # Check for forbidden characters to prevent injection
    if any(char in url for char in FORBIDDEN_CHARS):
        raise RepoValidationError("Repository URL contains invalid or potentially hazardous characters.")
        
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise RepoValidationError("Only secure HTTPS URLs are permitted (e.g., https://github.com/owner/repo).")
        
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise RepoValidationError("Currently only public GitHub repositories are supported.")
        
    match = GITHUB_URL_REGEX.match(url)
    if not match:
        raise RepoValidationError("URL does not match standard GitHub format (https://github.com/owner/repo).")
        
    owner = match.group("owner")
    repo = match.group("repo")
    
    # Additional guardrails on owner and repo length
    if len(owner) > 100 or len(repo) > 100:
        raise RepoValidationError("Repository owner or name is unusually long.")
        
    normalized_url = f"https://github.com/{owner}/{repo}.git"
    
    return {
        "owner": owner,
        "repo": repo,
        "normalized_url": normalized_url,
    }
