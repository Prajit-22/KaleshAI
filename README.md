# KaleshAI 😈

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

Leave "Local Ollama" enabled, and chat. You can also switch it off, enter an HTTPS OpenAI-compatible base URL, model and API key. Cloud API calls may cost money. The app does not load `.env` by itself; use environment variables or the sidebar. Never commit a key.

## RAG path

Upload a TXT, MD, or text-based PDF (2 MB/file, first 30 PDF pages). The app extracts text, creates overlapping chunks, retrieves them with lexical BM25, passes matching chunks to the selected LLM, and displays their source labels. Scanned PDFs need OCR. Lexical retrieval can miss synonyms. Retrieved labels show what was supplied to the model, not proof that every statement is supported.

Files: `app.py` is the Streamlit UI and persona; `rag.py` chunks and ranks text; `llm.py` calls OpenAI-compatible endpoints; `test_core.py` tests retrieval and the mocked client. Run tests with `python -m unittest -v test_core.py`. Uploaded files and conversation history live in the Streamlit session, not a database. The chosen model provider receives message text and retrieved excerpts. Don't upload secrets or sensitive records. This demo has no autonomous account access.
