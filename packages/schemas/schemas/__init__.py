from importlib.resources import files
import json

def load_json_schema(name: str) -> dict:
    """
    Load a schema by filename (without extension) from this package folder.
    Example: load_json_schema("resume_extraction")
    """
    p = files(__package__) / f"{name}.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))
