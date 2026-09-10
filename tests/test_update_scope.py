"""Check that the admin update preserves the existing public presentation."""
import ast
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicScopeTests(unittest.TestCase):
    def test_public_renderers_match_the_github_baseline(self):
        expected = json.loads((Path(__file__).with_name("public_source_baseline.json")).read_text())
        for filename, functions in expected.items():
            source = (ROOT / filename).read_text()
            nodes = {n.name: n for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for name, digest in functions.items():
                with self.subTest(file=filename, function=name):
                    actual = hashlib.sha256(ast.get_source_segment(source, nodes[name]).encode()).hexdigest()
                    self.assertEqual(actual, digest)

    def test_public_signin_and_landing_markup_is_unchanged(self):
        source = (ROOT / "app.py").read_text()
        function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "render_auth")
        markup = [ast.dump(c, include_attributes=False) for c in ast.walk(function)
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                  and isinstance(c.func.value, ast.Name) and c.func.value.id == "st"
                  and c.func.attr == "markdown"]
        expected = json.loads(Path(__file__).with_name("public_auth_markup.json").read_text())
        self.assertEqual(markup, expected)
