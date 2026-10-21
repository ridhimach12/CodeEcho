import ast
import re
import textwrap
from typing import Any
from backend.app.feature_extraction.models import ASTFeatures, ASTDiffProfile

FEATURE_NAMES = [
    "try_count",
    "except_count",
    "raise_count",
    "none_check_count",
    "if_count",
    "return_count",
    "loop_count",
    "function_def_count",
    "call_count",
    "assign_count",
    "assert_count",
    "with_count",
]

class ASTFeatureVisitor(ast.NodeVisitor):
    """
    Traverses an AST tree and collects structural programming constructs.
    """
    def __init__(self):
        self.try_count = 0
        self.except_count = 0
        self.raise_count = 0
        self.none_check_count = 0
        self.if_count = 0
        self.return_count = 0
        self.loop_count = 0
        self.function_def_count = 0
        self.call_count = 0
        self.assign_count = 0
        self.assert_count = 0
        self.with_count = 0
        self.class_def_count = 0
        self.exception_types: list[str] = []
        self.called_functions: list[str] = []

    def visit_Try(self, node: ast.Try):
        self.try_count += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.except_count += 1
        if node.type:
            if isinstance(node.type, ast.Name):
                self.exception_types.append(node.type.id)
            elif isinstance(node.type, ast.Attribute):
                self.exception_types.append(node.type.attr)
            elif isinstance(node.type, ast.Tuple):
                for elt in node.type.elts:
                    if isinstance(elt, ast.Name):
                        self.exception_types.append(elt.id)
                    elif isinstance(elt, ast.Attribute):
                        self.exception_types.append(elt.attr)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        self.raise_count += 1
        if node.exc:
            if isinstance(node.exc, ast.Name):
                self.exception_types.append(node.exc.id)
            elif isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                self.exception_types.append(node.exc.func.id)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # Check for 'is None' or 'is not None'
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Is, ast.IsNot)):
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    self.none_check_count += 1
                elif isinstance(node.left, ast.Constant) and node.left.value is None:
                    self.none_check_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self.if_count += 1
        # Check for idiom: 'if not x:' which frequently guards against None/empty
        if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
            self.none_check_count += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        self.if_count += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self.return_count += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_def_count += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.function_def_count += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self.call_count += 1
        if isinstance(node.func, ast.Name):
            self.called_functions.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.called_functions.append(node.func.attr)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        self.assign_count += 1
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.assign_count += 1
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.assign_count += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        self.assert_count += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        self.with_count += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.with_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_def_count += 1
        self.generic_visit(node)


class PythonASTParser:
    """
    Robust AST parser that handles standalone modules as well as fragmented diff hunks.
    Extracts structural programming features and detects behavioral mutations.
    """

    @classmethod
    def _parse_to_ast(cls, code: str) -> tuple[ast.AST | None, bool]:
        """
        Attempts multiple parsing strategies to parse code fragments into an AST.
        Returns: (parsed_ast, had_syntax_error)
        """
        if not code or not code.strip():
            return None, False

        # Strategy 1: Direct parsing as a complete module
        try:
            tree = ast.parse(code)
            return tree, False
        except (SyntaxError, IndentationError):
            pass

        # Strategy 2: Wrap dedented block in a dummy function context
        try:
            dedented = textwrap.dedent(code)
            wrapped = "def _codeecho_wrapper_context():\n" + textwrap.indent(dedented, "    ")
            tree = ast.parse(wrapped)
            return tree, False
        except (SyntaxError, IndentationError):
            pass

        # Strategy 3: Attempt statement-by-statement parsing
        statements = []
        for line in code.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            try:
                stmt_tree = ast.parse(line_str)
                statements.extend(stmt_tree.body)
            except (SyntaxError, IndentationError):
                continue

        if statements:
            mod = ast.Module(body=statements, type_ignores=[])
            return mod, True  # Partially parsed with some syntax errors

        return None, True

    @classmethod
    def extract_features(cls, code: str) -> ASTFeatures:
        """
        Extracts structural AST features from a code string.
        Gracefully handles syntax errors using fallback regex heuristics.
        """
        if not code or not code.strip():
            return ASTFeatures()

        tree, had_syntax_error = cls._parse_to_ast(code)

        if tree is not None:
            visitor = ASTFeatureVisitor()
            visitor.visit(tree)
            return ASTFeatures(
                try_count=visitor.try_count,
                except_count=visitor.except_count,
                raise_count=visitor.raise_count,
                none_check_count=visitor.none_check_count,
                if_count=visitor.if_count,
                return_count=visitor.return_count,
                loop_count=visitor.loop_count,
                function_def_count=visitor.function_def_count,
                call_count=visitor.call_count,
                assign_count=visitor.assign_count,
                assert_count=visitor.assert_count,
                with_count=visitor.with_count,
                class_def_count=visitor.class_def_count,
                exception_types=visitor.exception_types,
                called_functions=visitor.called_functions,
                has_syntax_error=had_syntax_error,
            )

        # Fallback Strategy: Pure Regex Heuristics for unparseable fragments
        return cls._fallback_regex_features(code)

    @classmethod
    def _fallback_regex_features(cls, code: str) -> ASTFeatures:
        """
        Regex-based structural feature extraction for severely truncated fragments.
        """
        try_count = len(re.findall(r"\btry\s*:", code))
        except_count = len(re.findall(r"\bexcept\b", code))
        raise_count = len(re.findall(r"\braise\b", code))
        none_check_count = len(re.findall(r"\bis\s+None\b|\bis\s+not\s+None\b|\bif\s+not\b", code))
        if_count = len(re.findall(r"\bif\b|\belif\b", code))
        return_count = len(re.findall(r"\breturn\b", code))
        loop_count = len(re.findall(r"\bfor\b|\bwhile\b", code))
        function_def_count = len(re.findall(r"\bdef\s+[a-zA-Z0-9_]+", code))
        call_count = len(re.findall(r"[a-zA-Z0-9_]+\s*\(", code))
        assign_count = len(re.findall(r"(?<!=)=(?!=)", code))
        assert_count = len(re.findall(r"\bassert\b", code))
        with_count = len(re.findall(r"\bwith\b", code))

        return ASTFeatures(
            try_count=try_count,
            except_count=except_count,
            raise_count=raise_count,
            none_check_count=none_check_count,
            if_count=if_count,
            return_count=return_count,
            loop_count=loop_count,
            function_def_count=function_def_count,
            call_count=call_count,
            assign_count=assign_count,
            assert_count=assert_count,
            with_count=with_count,
            has_syntax_error=True,
        )

    @classmethod
    def analyze_change(cls, deleted_code: str, added_code: str) -> ASTDiffProfile:
        """
        Compares deleted and added code fragments to construct an ASTDiffProfile.
        Calculates delta vector and detects key structural modifications.
        """
        del_feats = cls.extract_features(deleted_code)
        add_feats = cls.extract_features(added_code)

        del_vec = del_feats.to_vector()
        add_vec = add_feats.to_vector()
        delta_vec = [a - d for a, d in zip(add_vec, del_vec)]

        shifts: list[str] = []
        # Try/Except/Raise shifts
        if (add_feats.try_count + add_feats.except_count) > (del_feats.try_count + del_feats.except_count):
            shifts.append("added_exception_handling")
        elif (add_feats.try_count + add_feats.except_count) < (del_feats.try_count + del_feats.except_count):
            shifts.append("removed_exception_handling")

        if add_feats.raise_count > del_feats.raise_count:
            shifts.append("added_explicit_raise")

        # None check shifts
        if add_feats.none_check_count > del_feats.none_check_count:
            shifts.append("added_none_guard")
        elif add_feats.none_check_count < del_feats.none_check_count:
            shifts.append("removed_none_guard")

        # Conditional shifts
        if add_feats.if_count > del_feats.if_count:
            shifts.append("added_conditional_branching")
        elif add_feats.if_count < del_feats.if_count:
            shifts.append("simplified_conditional_branching")

        # Return statement shifts
        if add_feats.return_count > del_feats.return_count:
            shifts.append("added_return_statement")
        elif add_feats.return_count < del_feats.return_count:
            shifts.append("removed_return_statement")

        # Loop shifts
        if add_feats.loop_count > del_feats.loop_count:
            shifts.append("added_loop_iteration")

        # Function definition changes
        if add_feats.function_def_count != del_feats.function_def_count:
            shifts.append("modified_function_definition")

        # Function call shifts
        if add_feats.call_count > del_feats.call_count:
            shifts.append("added_function_calls")

        # Assertion shifts
        if add_feats.assert_count > del_feats.assert_count:
            shifts.append("added_assertion_checks")

        # Context manager shifts
        if add_feats.with_count > del_feats.with_count:
            shifts.append("added_context_manager")

        parsed_ok = not (del_feats.has_syntax_error or add_feats.has_syntax_error)

        return ASTDiffProfile(
            deleted_features=del_feats,
            added_features=add_feats,
            delta_vector=delta_vec,
            feature_names=FEATURE_NAMES,
            detected_shifts=shifts,
            parsed_successfully=parsed_ok,
        )
