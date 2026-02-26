import os
import runpy
import sys
from pathlib import Path

from dotenv import load_dotenv


def _has_query_flag(argv: list[str]) -> bool:
    return "--query" in argv or "-Q" in argv or "-q" in argv


def run_provider_entry(provider: str, mode: str, env_file: Path | None = None) -> None:
    root = Path(__file__).resolve().parents[1]
    root_env = root / ".env"

    if env_file and env_file.exists():
        load_dotenv(env_file, override=True)
        os.environ["ENV_FILE"] = str(env_file)
    elif root_env.exists():
        os.environ.setdefault("ENV_FILE", str(root_env))

    os.chdir(root)
    os.environ["MULTIMODAL_PROVIDER"] = provider

    argv = ["pinecone-multimodal-pipeline.py"]
    incoming = sys.argv[1:]

    if mode == "query":
        if not _has_query_flag(incoming):
            raise SystemExit(
                "Usage: python <entry_query.py> --query \"...\" [--namespace ...] [--top-k N]"
            )
        argv.extend(incoming)
    else:
        if "--load" not in incoming and "-L" not in incoming and "-l" not in incoming:
            argv.append("--load")
        argv.extend(incoming)

    sys.argv = argv
    runpy.run_path(str(root / "pinecone-multimodal-pipeline.py"), run_name="__main__")
