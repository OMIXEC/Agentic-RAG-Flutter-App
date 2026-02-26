import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ProviderScriptTests(unittest.TestCase):
    def test_ingest_openai_enforces_load(self):
        module = _load('ingest-openai.py', 'ingest_openai_script')
        with mock.patch.object(sys, 'argv', ['ingest-openai.py']):
            with mock.patch('runpy.run_path') as run_path:
                module.main()
        target = str((ROOT / 'providers' / 'pinecone-openai' / 'entry_ingest.py').resolve())
        run_path.assert_called_once_with(target, run_name='__main__')

    def test_query_vertex_requires_query_arg(self):
        module = _load('query-vertex.py', 'query_vertex_script')
        with mock.patch.object(sys, 'argv', ['query-vertex.py']):
            with self.assertRaises(SystemExit):
                module.main()

    def test_legacy_wrapper_switches_to_query(self):
        module = _load('pinecone-legacy-rag.py', 'legacy_wrapper_script')
        with mock.patch.object(sys, 'argv', ['pinecone-legacy-rag.py', '--query', 'hello']):
            with mock.patch('runpy.run_path') as run_path:
                module.main()
        run_path.assert_called_once_with('query-legacy.py', run_name='__main__')

    def test_pinecone_openai_load_dispatches_ingest(self):
        module = _load('pinecone-openai-load.py', 'openai_load_wrapper_script')
        with mock.patch.object(sys, 'argv', ['pinecone-openai-load.py']):
            with mock.patch('runpy.run_path') as run_path:
                module.main()
        target = str((ROOT / 'providers' / 'pinecone-openai' / 'entry_ingest.py').resolve())
        run_path.assert_called_once_with(target, run_name='__main__')

    def test_pinecone_openai_load_dispatches_query(self):
        module = _load('pinecone-openai-load.py', 'openai_load_wrapper_script_query')
        with mock.patch.object(sys, 'argv', ['pinecone-openai-load.py', '--query', 'hello']):
            with mock.patch('runpy.run_path') as run_path:
                module.main()
        target = str((ROOT / 'providers' / 'pinecone-openai' / 'entry_query.py').resolve())
        run_path.assert_called_once_with(target, run_name='__main__')


if __name__ == '__main__':
    unittest.main()
