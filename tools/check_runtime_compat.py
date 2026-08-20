from __future__ import print_function, unicode_literals

import ast
import os
import sys


RUNTIME_FILES = [
    "game/openai_tts_mod/__init__.py",
    "game/openai_tts_mod/adapter.py",
    "game/openai_tts_mod/core.py",
]


class CompatibilityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_JoinedStr(self, node):
        self.errors.append("f-string syntax is not supported by Python 2.7")
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self.errors.append("variable annotation syntax is not supported by Python 2.7")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        annotations = [argument.annotation for argument in node.args.args if argument.annotation]
        annotations.extend(
            argument.annotation for argument in getattr(node.args, "kwonlyargs", []) if argument.annotation
        )
        if annotations or node.returns:
            self.errors.append("function annotation syntax is not supported by Python 2.7")
        if getattr(node.args, "kwonlyargs", []):
            self.errors.append("keyword-only arguments are not supported by Python 2.7")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.errors.append("async syntax is not supported by Python 2.7")
        self.generic_visit(node)

    def visit_Await(self, node):
        self.errors.append("await syntax is not supported by Python 2.7")
        self.generic_visit(node)

    def visit_YieldFrom(self, node):
        self.errors.append("yield from syntax is not supported by Python 2.7")
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.errors.append("nonlocal syntax is not supported by Python 2.7")

    def visit_NamedExpr(self, node):
        self.errors.append("assignment expressions are not supported by Python 2.7")
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split(".")[0] in ("pathlib", "dataclasses"):
                self.errors.append("%s is not in the Python 2.7 standard library" % alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if module.split(".")[0] in ("pathlib", "dataclasses"):
            self.errors.append("%s is not in the Python 2.7 standard library" % module)
        self.generic_visit(node)


def compatibility_errors(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return ["source does not parse: %s" % error]
    visitor = CompatibilityVisitor()
    visitor.visit(tree)
    return visitor.errors


def check_runtime_files(project_root):
    failures = []
    for relative_path in RUNTIME_FILES:
        path = os.path.join(project_root, *relative_path.split("/"))
        with open(path, "r", encoding="utf-8") as source_file:
            errors = compatibility_errors(source_file.read())
        for error in errors:
            failures.append("%s: %s" % (relative_path, error))
    return failures


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failures = check_runtime_files(project_root)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(
        "Python 2.7-oriented runtime syntax guard passed (%d files); "
        "this is not a runtime compatibility proof." % len(RUNTIME_FILES)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
