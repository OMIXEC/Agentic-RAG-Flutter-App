import runpy
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    query_mode = "--query" in sys.argv or "-Q" in sys.argv or "-q" in sys.argv
    filename = "entry_query.py" if query_mode else "entry_ingest.py"
    target = root / "providers" / "pinecone-gcp-vertex" / filename
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
