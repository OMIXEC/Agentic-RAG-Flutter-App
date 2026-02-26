import subprocess
import sys


PROVIDERS = {
    'openai': ('ingest-openai.py', 'query-openai.py'),
    'vertex': ('ingest-vertex.py', 'query-vertex.py'),
    'aws': ('ingest-aws.py', 'query-aws.py'),
    'legacy': ('ingest-legacy.py', 'query-legacy.py'),
}


def _ask(prompt: str, default: str = '') -> str:
    suffix = f' [{default}]' if default else ''
    value = input(f'{prompt}{suffix}: ').strip()
    return value or default


def _run(command: list[str]) -> int:
    print(f"\n$ {' '.join(command)}")
    result = subprocess.run(command)
    return result.returncode


def main() -> None:
    action = _ask('Action (ingest/query/both)', 'both').lower()
    provider_key = _ask('Provider (openai/vertex/aws/legacy/all)', 'all').lower()
    namespace = _ask('Namespace', 'global')
    top_k = _ask('Top K', '4')
    query = ''
    if action in {'query', 'both'}:
        query = _ask('Query text', 'What do we know from recent news and media?')

    providers = list(PROVIDERS.keys()) if provider_key == 'all' else [provider_key]
    failures: list[tuple[str, str, int]] = []

    for provider in providers:
        if provider not in PROVIDERS:
            print(f'Skipping unknown provider: {provider}')
            continue
        ingest_script, query_script = PROVIDERS[provider]
        if action in {'ingest', 'both'}:
            code = _run([sys.executable, ingest_script, '--namespace', namespace])
            if code != 0:
                failures.append((provider, 'ingest', code))
        if action in {'query', 'both'}:
            code = _run([sys.executable, query_script, '--namespace', namespace, '--top-k', str(top_k), '--query', query])
            if code != 0:
                failures.append((provider, 'query', code))

    print('\nSummary:')
    if not failures:
        print('All selected provider runs completed successfully.')
        return
    for provider, step, code in failures:
        print(f'- {provider} {step} failed with exit code {code}')
    raise SystemExit(1)


if __name__ == '__main__':
    main()
