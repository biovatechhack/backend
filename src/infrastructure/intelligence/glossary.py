import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def load_glossary() -> dict:
    """Load Darija glossary from project root / src/data/"""
    
    # Reliable path from anywhere in the project
    project_root = Path(__file__).resolve().parents[3]   # goes up to backend root
    glossary_path = project_root / "src" / "data" / "darija_glossary.json"

    if not glossary_path.exists():
        raise FileNotFoundError(
            f"Darija glossary not found at: {glossary_path}\n"
            "Please make sure the file exists at: src/data/darija_glossary.json"
        )

    with open(glossary_path, encoding="utf-8") as f:
        return json.load(f)