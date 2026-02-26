import os
import runpy
import sys

os.environ['MULTIMODAL_PROVIDER'] = 'legacy_multimodal'


def main() -> None:
    argv = ['pinecone-multimodal-pipeline.py']
    if '--load' not in sys.argv and '-L' not in sys.argv and '-l' not in sys.argv:
        argv.append('--load')
    argv.extend(sys.argv[1:])
    sys.argv = argv
    runpy.run_path('pinecone-multimodal-pipeline.py', run_name='__main__')


if __name__ == '__main__':
    main()
