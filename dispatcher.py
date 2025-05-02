from pathlib import Path
from typing import List, Dict

from parsers import parse_python
from storage import save_entities

PARSER_MAP = {
    ".py": parse_python,
}

def dispatch_file(path: Path):
    parser = PARSER_MAP.get(path.suffix.lower())
    if parser is None:
        return
    
    save_entities(parser(path.resolve()))