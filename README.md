# KaleshAI 😈

**Live demo:** https://kaleshai.streamlit.app

A mischievous Hinglish chatbot with a real LLM-backed chat flow and optional document Q&A. It is an evil-ish twin: quick roasts, light gaali, but still answers the question. KaleshAI is an independent demo, not an Instinct product or replica.

## Run locally

Python 3.10+ and Ollama are required for the default setup. Install Ollama from https://ollama.com/, then:

```bash
ollama pull llama3.2
ollama serve
```

In another terminal:

```bash
git clone https://github.com/Prajit-22/KaleshAI.git
cd KaleshAI
python -m venv .venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Turn on the "Local Ollama" toggle in the sidebar, and chat. You can also switch it off, enter an HTTPS OpenAI-compatible base URL, model and API key. Cloud API calls may cost money. The app does not load `.env` by itself; use environment variables or the sidebar. Never commit a key.

## Hosted use

The app starts with Local Ollama off and Groq defaults prefilled (`https://api.groq.com/openai/v1`, `llama-3.1-8b-instant`). No key is stored in the repo: paste your own key in the sidebar, or set `OPENAI_API_KEY` (or `GROQ_API_KEY`) as an environment variable or Streamlit secret, then reboot the app. On Streamlit Community Cloud, deploy `app.py` from this repo.

## RAG path

Upload a TXT, MD, or text-based PDF (2 MB/file, first 30 PDF pages). The app extracts text, creates overlapping chunks, retrieves them with lexical BM25, passes matching chunks to the selected LLM, and displays their source labels. Scanned PDFs need OCR. Lexical retrieval can miss synonyms. Retrieved labels show what was supplied to the model, not proof that every statement is supported.

Files: `app.py` is the Streamlit UI and persona; `rag.py` chunks and ranks text; `llm.py` calls OpenAI-compatible endpoints; `test_core.py` tests retrieval and the mocked client. Run the 20 offline tests with `python -m unittest -v test_core.py`; GitHub Actions runs them on Python 3.10-3.12 for every push and pull request. Uploaded files and conversation history live in the Streamlit session, not a database. The chosen model provider receives message text and retrieved excerpts. Don't upload secrets or sensitive records. This demo has no autonomous account access.

## Retrieval index lifecycle

`BM25Index(chunks)` takes an immutable snapshot of the chunk list. Later edits
to the input list do not change indexed text, source labels, or scores. Build a
new index after changing the corpus. `search(query, k)` requires `k > 0`; blank
queries and queries without matching tokens return no hits. These boundaries
are covered by regression tests, including input-list replacement, clearing,
and appending. Tests mock the LLM client and make no paid model calls.

## Provider errors

`llm.complete` raises `RuntimeError` for every provider-side failure: HTTP errors, unreachable host, read timeout, a non-JSON body, or a reply without `choices[0].message`. Misconfiguration (bad URL scheme, plaintext remote host, blank model) raises `ValueError`. API keys are redacted from error text.

## Chunking

`chunk_text` splits on whitespace into windows of `size` words that share
`overlap` words. Chunking stops as soon as a window reaches the end of the
text, so a short document never produces a second chunk that only repeats the
end of the first (which would show up as a duplicate retrieval hit).
