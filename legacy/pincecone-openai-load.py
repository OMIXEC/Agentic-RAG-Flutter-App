import runpy
from pathlib import Path


def main() -> None:
    # Deprecated typo-compatible alias.
    target = Path(__file__).resolve().parent / "pinecone-openai-load.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
