import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from providers.entrypoint_common import run_provider_entry


ENV_FILE = Path(__file__).resolve().with_name(".env")


def main() -> None:
    run_provider_entry(provider="vertex", mode="query", env_file=ENV_FILE)


if __name__ == "__main__":
    main()
