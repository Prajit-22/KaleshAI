import unittest
from unittest.mock import patch
from io import BytesIO
from rag import BM25Index, Chunk, chunk_text
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

    def test_no_duplicate_tail_chunk_when_text_ends_inside_overlap(self):
        # 8 words, size 5, overlap 2: the second window already ends the text.
        words = " ".join(f"w{i}" for i in range(8))
        chunks = chunk_text(words, "a", size=5, overlap=2)
        self.assertEqual([c.text for c in chunks], ["w0 w1 w2 w3 w4", "w3 w4 w5 w6 w7"])
        # 5 words fit one window exactly; the old code emitted a 2-word repeat.
        exact = chunk_text("w0 w1 w2 w3 w4", "a", size=5, overlap=2)
        self.assertEqual([(c.number, c.text) for c in exact], [(1, "w0 w1 w2 w3 w4")])
        # 6 words: the tail adds one new word, so it stays.
        six = chunk_text("w0 w1 w2 w3 w4 w5", "a", size=5, overlap=2)
        self.assertEqual([c.text for c in six], ["w0 w1 w2 w3 w4", "w3 w4 w5"])

    def test_chunks_cover_text_without_contained_chunks(self):
        for n in range(0, 40):
            text = " ".join(f"w{i}" for i in range(n))
            chunks = chunk_text(text, "a", size=7, overlap=3)
            self.assertEqual([c.number for c in chunks], list(range(1, len(chunks) + 1)))
            if n:
                self.assertIn(f"w{n - 1}", chunks[-1].text.split())
            for earlier, later in zip(chunks, chunks[1:]):
                self.assertFalse(later.text in earlier.text, (n, later.text))
        self.assertEqual(chunk_text("", "a"), [])


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


class IndexSnapshotTests(unittest.TestCase):
    def test_replacing_input_chunk_does_not_relabel_a_match(self):
        chunks = [Chunk("python.md", 1, "python services")]
        index = BM25Index(chunks)
        chunks[0] = Chunk("fruit.md", 1, "mango fruit")
        hits = index.search("python")
        self.assertEqual(hits[0][0].source, "python.md")
        self.assertEqual(hits[0][0].text, "python services")

    def test_clearing_input_does_not_empty_existing_index(self):
        chunks = [Chunk("a.md", 1, "python services")]
        index = BM25Index(chunks)
        chunks.clear()
        self.assertEqual(index.search("python")[0][0].source, "a.md")

    def test_appending_input_does_not_change_scores(self):
        chunks = [Chunk("a.md", 1, "python services")]
        index = BM25Index(chunks)
        before = index.search("python")
        chunks.append(Chunk("b.md", 1, "unrelated words"))
        self.assertEqual(index.search("python"), before)

    def test_index_snapshot_is_immutable(self):
        index = BM25Index([Chunk("a.md", 1, "python")])
        self.assertIsInstance(index.chunks, tuple)

    def test_nonpositive_k_rejected_even_for_empty_queries_or_corpora(self):
        for chunks in ([], [Chunk("a.md", 1, "python")]):
            for query in ("", "python"):
                for k in (0, -1):
                    with self.subTest(chunks=chunks, query=query, k=k):
                        with self.assertRaisesRegex(ValueError, "k must be positive"):
                            BM25Index(chunks).search(query, k=k)

    def test_limit_and_descending_scores(self):
        index = BM25Index([Chunk("a", 1, "python python python"),
                           Chunk("b", 1, "python and other words"),
                           Chunk("c", 1, "mango fruit")])
        hits = index.search("python", k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0].source, "a")

    def test_punctuation_query_and_tokenless_documents(self):
        index = BM25Index([Chunk("a", 1, "!!!")])
        self.assertEqual(index.search("!!!"), [])
        self.assertEqual(index.search("python"), [])



class ClientFailureTests(unittest.TestCase):
    def _serve(self, body, status=200):
        import http.server, threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        return f"http://127.0.0.1:{server.server_port}/v1"

    def test_non_json_body_becomes_runtime_error(self):
        url = self._serve(b"<html>gateway page</html>")
        with self.assertRaisesRegex(RuntimeError, "not valid JSON"):
            complete([], url, "m")

    def test_invalid_utf8_body_becomes_runtime_error(self):
        url = self._serve(b"\xff\xfe")
        with self.assertRaisesRegex(RuntimeError, "not valid JSON"):
            complete([], url, "m")

    def test_unexpected_shape_becomes_runtime_error(self):
        url = self._serve(b'{"choices": []}')
        with self.assertRaisesRegex(RuntimeError, "unexpected chat response"):
            complete([], url, "m")

    def test_valid_response_returns_content(self):
        url = self._serve(b'{"choices": [{"message": {"content": "hi"}}]}')
        self.assertEqual(complete([], url, "m"), "hi")

    def test_read_timeout_becomes_runtime_error(self):
        with patch("llm.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                complete([], "http://127.0.0.1:9/v1", "m", timeout=3)

    def test_blank_model_rejected(self):
        with self.assertRaises(ValueError):
            complete([], "http://127.0.0.1:9/v1", "  ")


if __name__ == "__main__":
    unittest.main()
