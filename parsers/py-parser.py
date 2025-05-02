import ast


class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        func_name = self._get_func_name(node.func)
        if func_name:
            self.calls.append(
                {
                    "function": func_name,
                    "lineno": node.lineno,
                    "col_offset": node.col_offset,
                }
            )
        self.generic_visit(node)

    def _get_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_func_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None


with open("1.py", "r", encoding="utf-8") as file:
    source_code = file.read()

tree = ast.parse(source_code)
visitor = FunctionCallVisitor()
visitor.visit(tree)

for call in visitor.calls:
    print(
        f"Вызов функции: {call['function']} (строка {call['lineno']}, позиция {call['col_offset']})"
    )
