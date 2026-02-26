import runpy
import sys


def main() -> None:
    args = sys.argv[1:]
    is_query = '--query' in args or '-Q' in args or '-q' in args
    target = 'query-legacy.py' if is_query else 'ingest-legacy.py'
    sys.argv = [target, *args]
    runpy.run_path(target, run_name='__main__')


if __name__ == '__main__':
    main()
