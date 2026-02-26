import runpy
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parent / "providers" / "pinecone-openai" / "entry_ingest.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
