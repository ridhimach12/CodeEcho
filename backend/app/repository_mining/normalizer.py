import re
import io
import tokenize
import keyword

# Common Python built-ins to preserve during variable masking
BUILTINS = {
    "print", "len", "range", "str", "int", "float", "bool", "list", "dict",
    "set", "tuple", "isinstance", "issubclass", "getattr", "setattr", "hasattr",
    "open", "enumerate", "zip", "map", "filter", "any", "all", "min", "max",
    "sum", "sorted", "reversed", "iter", "next", "super", "id", "type",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "RuntimeError",
    "AttributeError", "FileNotFoundError", "ZeroDivisionError", "self", "cls"
}

def strip_comments_and_docstrings(source: str) -> str:
    """
    Strips single line comments and docstrings from Python source code
    using the standard library tokenize module to avoid syntax corruption.
    Falls back gracefully if syntax is incomplete/fragmented (e.g., partial diff hunks).
    """
    if not source.strip():
        return ""

    try:
        io_obj = io.StringIO(source)
        out = []
        prev_toktype = tokenize.INDENT
        last_lineno = -1
        last_col = 0

        tokens = tokenize.generate_tokens(io_obj.readline)
        for tok in tokens:
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]

            if token_type == tokenize.COMMENT:
                continue
            elif token_type == tokenize.STRING:
                if prev_toktype in (tokenize.INDENT, tokenize.NL, tokenize.NEWLINE) or last_lineno == -1:
                    # Likely a standalone docstring
                    continue

            out.append(token_string)
            prev_toktype = token_type
            last_lineno = end_line
            last_col = end_col

        return " ".join(out)
    except Exception:
        # Fallback for diff fragments: regex-based comment removal
        lines = []
        for line in source.splitlines():
            line_no_comment = re.sub(r"#.*$", "", line).rstrip()
            if line_no_comment.strip():
                lines.append(line_no_comment.strip())
        return "\n".join(lines)


def canonicalize_identifiers(source: str) -> str:
    """
    Replaces user-defined local variables with canonical tokens (VAR_1, VAR_2)
    while preserving Python keywords, builtins, and syntax structure.
    This eliminates superficial rename noise across repositories.
    """
    if not source.strip():
        return ""

    try:
        tokens = []
        var_map: dict[str, str] = {}
        var_counter = 1

        io_obj = io.StringIO(source)
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]

            if token_type == tokenize.NAME:
                if (token_string in keyword.kwlist or 
                    token_string in BUILTINS or 
                    token_string.startswith("__")):
                    tokens.append(token_string)
                else:
                    if token_string not in var_map:
                        var_map[token_string] = f"VAR_{var_counter}"
                        var_counter += 1
                    tokens.append(var_map[token_string])
            elif token_type in (tokenize.COMMENT, tokenize.NL):
                continue
            else:
                tokens.append(token_string)

        return " ".join(tokens)
    except Exception:
        # Fallback: simple token normalization
        return re.sub(r"\s+", " ", source).strip()


def normalize_code_diff(added_code: str, deleted_code: str) -> str:
    """
    Produces a normalized representation of a code change hunk.
    Combines stripped, canonicalized deleted and added fragments.
    """
    clean_deleted = strip_comments_and_docstrings(deleted_code)
    clean_added = strip_comments_and_docstrings(added_code)

    canon_deleted = canonicalize_identifiers(clean_deleted)
    canon_added = canonicalize_identifiers(clean_added)

    diff_parts = []
    if canon_deleted.strip():
        diff_parts.append(f"[-] {canon_deleted}")
    if canon_added.strip():
        diff_parts.append(f"[+] {canon_added}")

    return "\n".join(diff_parts) if diff_parts else ""
