import os
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV_FILE = Path(__file__).resolve().with_name('.env')
ROOT_ENV_FILE = ROOT / '.env'


def main() -> None:
    os.environ['MULTIMODAL_PROVIDER'] = 'vertex'
    env_file = LOCAL_ENV_FILE if LOCAL_ENV_FILE.exists() else ROOT_ENV_FILE
    os.environ['ENV_FILE'] = str(env_file)
    os.environ.setdefault('PINECONE_NAMESPACE', 'vertex')

    argv = ['pinecone-multimodal-pipeline.py']
    if '--query' in sys.argv or '-Q' in sys.argv or '-q' in sys.argv:
        argv.extend(sys.argv[1:])
    else:
        if '--load' not in sys.argv and '-L' not in sys.argv and '-l' not in sys.argv:
            argv.append('--load')
        argv.extend(sys.argv[1:])

    sys.argv = argv
    runpy.run_path(str(ROOT / 'pinecone-multimodal-pipeline.py'), run_name='__main__')


if __name__ == '__main__':
    main()
