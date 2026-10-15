import unittest
from unittest.mock import patch
from pathlib import Path
from rag import Chunk
from workbench import TASKS, document_context, reply_export, conversation_export
from websearch import WebResult


class WorkbenchTests(unittest.TestCase):
    def test_small_document_includes_every_chunk(self):
        context, labels, note = document_context([Chunk('a', 1, 'hello'), Chunk('a', 2, 'world')])
        self.assertEqual(labels, ['a #1', 'a #2'])
        self.assertIn('[a #2]\nworld', context)
        self.assertIn('All extracted text', note)

    def test_large_document_samples_with_true_labels_and_bounded_context(self):
        chunks = [Chunk('long', i, str(i) + ' word' * 60) for i in range(1, 81)]
        context, labels, note = document_context(chunks, budget=1400)
        self.assertLessEqual(len(context), 1400)
        self.assertIn('long #1', labels)
        self.assertIn('long #80', labels)
        self.assertIn('Partial coverage', note)
        numbers = [int(label.split('#')[1]) for label in labels]
        self.assertEqual(numbers, sorted(numbers))

    def test_empty_and_oversized_chunks_do_not_misrepresent_coverage(self):
        self.assertEqual(document_context([])[1], [])
        self.assertIn('No readable', document_context([])[2])
        self.assertIn('Partial coverage', document_context([Chunk('a', 1, 'x' * 200)], 100)[2])
        with self.assertRaises(ValueError):
            document_context([], 0)

    def test_tasks_require_evidence_and_do_not_invent_owners(self):
        self.assertIn('not specified', TASKS['Action items'])
        self.assertIn('source labels', TASKS['Summary'])

    def test_export_keeps_text_unicode_sources_and_coverage(self):
        msg = {'role': 'assistant', 'content': 'Notes: café हिंदी $50', 'sources': ['a #2'],
               'coverage': 'Partial coverage', 'web': [WebResult('Python', 'https://www.python.org/', '')]}
        output = reply_export(msg)
        for expected in ('café हिंदी $50', 'a #2', 'Partial coverage', 'https://www.python.org/'):
            self.assertIn(expected, output)
        self.assertIn('## You', conversation_export([{'role': 'user', 'content': 'hello'}, msg]))
        self.assertIn('## KaleshAI', conversation_export([msg]))

    def test_ui_summary_and_export_with_mocked_provider(self):
        import os
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest('Install requirements.txt for UI smoke test')
        from io import BytesIO
        class Upload(BytesIO):
            name = 'meeting.txt'
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-placeholder'}), \
             patch('streamlit.file_uploader', return_value=[Upload(b'Asha will send the report on Friday. Budget is 50 rupees.')]), \
             patch('llm.complete', return_value='Asha: send report on Friday [1: meeting.txt #1].') as client:
            app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
            self.assertFalse(app.exception)
            next(b for b in app.button if b.label == 'Run document job').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(client.call_count, 1)
            message = client.call_args.args[0][-1]['content']
            self.assertIn('Summarize', message)
            self.assertIn('Asha will send', message)
            self.assertIn('All extracted text', message)
            self.assertTrue(any('Answer to save' == s.label for s in app.selectbox))
            self.assertEqual(app.session_state.messages[-1]['sources'], ['1: meeting.txt #1'])
