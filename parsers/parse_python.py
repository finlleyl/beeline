import ast
import io
from pathlib import Path
import tokenize
from typing import List, Dict


def parse_python(path: Path) -> List[Dict]:

    source = path.read_text(encoding="utf-8")
    uri = path.as_uri()

    comment_map: Dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            ln = tok.start[0]
            txt = tok.string.lstrip("#").strip()
            comment_map.setdefault(ln, []).append(txt)

    entities: List[Dict] = []

    class Analyzer(ast.NodeVisitor):
        def __init__(self):
            self.entities: List[Dict] = []
            self.current_entity: Dict = None

        def visit_ClassDef(self, node: ast.ClassDef):
            uri = path.as_uri()
            entity = {
                "id": f"{uri}::{node.name}",
                "name": node.name,
                "type": "class",
                "file": uri,
                "inherits": [
                    base.id if isinstance(base, ast.Name) else ast.unparse(base)
                    for base in node.bases
                ],
                "relations": {"methods": [], "calls": [], "called_by": []},
            }
            prev = self.current_entity
            self.current_entity = entity
            self.entities.append(entity)
            self.generic_visit(node)
            self.current_entity = prev

        def visit_FunctionDef(self, node: ast.FunctionDef):
            uri = path.as_uri()
            if self.current_entity and self.current_entity.get("type") == "class":
                parent = self.current_entity
                qname = f"{parent['id']}.{node.name}"
                parent["relations"]["methods"].append(qname)
                ent_type = "function"
                ent_id = qname
            else:
                ent_type = "function"
                ent_id = f"{uri}::{node.name}"
            entity = {
                "id": ent_id,
                "name": node.name,
                "type": ent_type,
                "file": uri,
                "inherits": [],
                "relations": {"calls": [], "called_by": []},
            }
            self.entities.append(entity)
            prev = self.current_entity
            self.current_entity = entity
            self.generic_visit(node)
            self.current_entity = prev

        def visit_Call(self, node: ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            else:
                name = ast.unparse(func)
            if self.current_entity:
                self.current_entity["relations"]["calls"].append(name)
            self.generic_visit(node)

    Analyzer.visit(ast.parse(source))

    return entities


result = parse_python(Path("parsers/pyparser.py").resolve())
