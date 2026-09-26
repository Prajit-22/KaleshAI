import unittest
from unittest.mock import patch
from io import BytesIO
from rag import BM25Index, chunk_text
from llm import complete


class RagTests(unittest.TestCase):
    def test_retrieves_relevant_source(self):
        chunks = chunk_text("Python builds useful services. " * 12, "python.md", size=15, overlap=3)
        chunks += chunk_text("Mangoes are sweet fruits. " * 12, "fruit.md", size=15, overlap=3)
        hits = BM25Index(chunks).search("Python services", k=2)
        self.assertTrue(hits)
        self.assertEqual(hits[0][0].source, "python.md")

    def test_empty_and_no_match(self):
        self.assertEqual(BM25Index([]).search("anything"), [])
        self.assertEqual(BM25Index(chunk_text("hello world", "a")).search("zebra"), [])

    def test_overlap_and_validation(self):
        chunks = chunk_text("one two three four five six", "a", size=4, overlap=2)
        self.assertEqual(chunks[0].text, "one two three four")
        self.assertTrue(chunks[1].text.startswith("three four"))
        with self.assertRaises(ValueError):
            chunk_text("hello", "a", size=2, overlap=2)


class ClientTests(unittest.TestCase):
    def test_rejects_plaintext_remote(self):
        with self.assertRaises(ValueError):
            complete([], "http://api.example.com/v1", "model")

    @patch("llm.urllib.request.urlopen")
    def test_openai_compatible_response(self, urlopen):
        urlopen.return_value.__enter__.return_value = BytesIO(b'{"choices":[{"message":{"content":"Namaste, saale!"}}]}')
        result = complete([{"role":"user","content":"hi"}], "http://localhost:11434/v1", "llama3.2")
        self.assertEqual(result, "Namaste, saale!")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11434/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
