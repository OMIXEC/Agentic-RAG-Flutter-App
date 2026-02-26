import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / 'pinecone-db.py'
spec = importlib.util.spec_from_file_location('pinecone_db_entry', MODULE_PATH)
entry = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(entry)


class PineconeDbEntryTests(unittest.TestCase):
    def test_select_provider_auto_vertex(self):
        with mock.patch.dict(
            os.environ,
            {
                'MULTIMODAL_PROVIDER': '',
                'EMBEDDING_PROVIDER': 'auto',
                'GOOGLE_CLOUD_PROJECT': 'proj',
                'GOOGLE_VERTEX_ACCESS_TOKEN': 'tok',
            },
            clear=False,
        ):
            self.assertEqual(entry._select_multimodal_provider(), 'vertex')

    def test_select_provider_auto_openai(self):
        with mock.patch.dict(
            os.environ,
            {
                'MULTIMODAL_PROVIDER': '',
                'EMBEDDING_PROVIDER': 'auto',
                'GOOGLE_CLOUD_PROJECT': '',
                'GOOGLE_VERTEX_ACCESS_TOKEN': '',
            },
            clear=False,
        ):
            self.assertEqual(entry._select_multimodal_provider(), 'openai_clip')

    def test_select_provider_explicit_legacy(self):
        with mock.patch.dict(
            os.environ,
            {
                'MULTIMODAL_PROVIDER': 'legacy_multimodal',
            },
            clear=False,
        ):
            self.assertEqual(entry._select_multimodal_provider(), 'legacy_multimodal')

    def test_main_legacy_txt_only(self):
        with mock.patch.dict(os.environ, {'LEGACY_TXT_ONLY': 'true'}, clear=False):
            with mock.patch('runpy.run_path') as mocked_run:
                entry.main()
                mocked_run.assert_called_once_with('pinecone-legacy-rag.py', run_name='__main__')

    def test_main_dispatches_to_ingest_script(self):
        with mock.patch.dict(
            os.environ,
            {'LEGACY_TXT_ONLY': 'false', 'MULTIMODAL_PROVIDER': 'openai_clip'},
            clear=False,
        ):
            with mock.patch.object(sys, 'argv', ['pinecone-db.py', '--load']):
                with mock.patch('runpy.run_path') as mocked_run:
                    entry.main()
                    mocked_run.assert_called_once_with('ingest-openai.py', run_name='__main__')

    def test_main_dispatches_to_query_script(self):
        with mock.patch.dict(
            os.environ,
            {'LEGACY_TXT_ONLY': 'false', 'MULTIMODAL_PROVIDER': 'vertex'},
            clear=False,
        ):
            with mock.patch.object(sys, 'argv', ['pinecone-db.py', '--query', 'hello']):
                with mock.patch('runpy.run_path') as mocked_run:
                    entry.main()
                    mocked_run.assert_called_once_with('query-vertex.py', run_name='__main__')


if __name__ == '__main__':
    unittest.main()
