# KaleshAI

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

The app starts with Local Ollama off and Groq defaults prefilled (`https://api.groq.com/openai/v1`, `openai/gpt-oss-20b`). No key is stored in the repo: paste your own key in the sidebar, or set `OPENAI_API_KEY` (or `GROQ_API_KEY`) as an environment variable or Streamlit secret, then reboot the app. On Streamlit Community Cloud, deploy `app.py` from this repo.

Groq lists GPT-OSS 20B as a production text/chat model. Its current [models page](https://console.groq.com/docs/models) labels Llama 3.1 8B Instant as Enterprise, so that model can return `model_not_found` on accounts without access. If you already have the app open, replace the sidebar Model with `openai/gpt-oss-20b` and send a new message. A fresh page uses the new default unless `OPENAI_MODEL` overrides it. Provider access and rate limits depend on your account; never share your key in chat.

## Arcade interface & language

The interface uses original generated caricature garage artwork with a male biker and a stylish adult woman biker, cats and dogs with a teal, violet and amber palette,
a torn cloth KALESH AI banner painted into the wall, an original cat favicon, an olive-teal garage control drawer,
soft chat-entry motion and drawer/button transitions. The male biker has longer hair and a lighter complexion. No copied game assets,
external fonts, JavaScript animation libraries or third-party art downloads are used. The compressed WebP is bundled inline (about 177 KB of image data). The device's
`prefers-reduced-motion` setting disables motion.

The persona defaults to Roman-script Hinglish and treats casual swearing aimed at
the bot as friendly banter, not a reason to refuse. It avoids identity-based slurs
and targeted harassment. Provider safety rules still apply: prompt examples cannot
guarantee that every model will follow the language or accept every phrase.
The app-flow test uses a mocked reply; it does not prove live model behaviour.

## RAG path

Upload a TXT, MD, or text-based PDF (2 MB/file, first 30 PDF pages). The app extracts text, creates overlapping chunks, retrieves them with lexical BM25, passes matching chunks to the selected LLM, and displays their source labels. Scanned PDFs need OCR. Lexical retrieval can miss synonyms. Retrieved labels show what was supplied to the model, not proof that every statement is supported.

Files: `app.py` is the Streamlit UI and persona; `rag.py` chunks and ranks text; `llm.py` calls OpenAI-compatible endpoints; `websearch.py` is the keyless web search; `test_core.py` and `test_websearch.py` test retrieval, the mocked client and web search. Run the offline tests with `python -m unittest discover -v`; GitHub Actions runs them on Python 3.10-3.14 for every push and pull request. Uploaded files and conversation history live in the Streamlit session, not a database. The chosen model provider receives message text and retrieved excerpts. Don't upload secrets or sensitive records. This demo has no autonomous account access.

## Web search

Turn on "Search the web" in the main-page "Web search & documents" popover. For each question that looks like a lookup (a question mark or three or more words; greetings are skipped), the app searches the web first and gives the top results (title, URL and snippet only, never full pages) to the model, which is asked to cite them as `[web #n]`. The links appear under the reply. No search API key is needed.

How it works: `websearch.py` is standard-library only. It tries Bing's HTML results, then DuckDuckGo's HTML results, then the Wikipedia search API, and uses the first one that returns results. Chatty questions are rewritten into keywords first ("what is the latest X?" becomes "latest X"), and a lightweight keyword check tries the next backend if results look unrelated. Multi-intent requests separate the web lookup from a follow-up about uploaded documents; common resume-scoring requests become "resume score checker website". If every available backend looks low-relevance, the first nonempty results are returned with a clear caveat instead of pretending the search failed. Scraped result pages are not a stable API: a search engine can block a hosting provider's IP or change its layout. When every backend fails, the reply says so, the model is told not to claim it searched, and chat keeps working. "Test web search" in the same popover checks the backends from the server the app runs on. Search results are untrusted text and are passed to the model as reference material, not instructions. Your question text goes to the search engine. Local Ollama can use web search too.

Offline tests for the parsers, fallback order, failure handling and prompt building are in `test_websearch.py`; no test touches the network.

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

## Document workshop and downloads

Open **Web search & documents** on the main page. Upload TXT, MD or text-based
PDF files, then choose **Work with** to scope chat or a document job to one file
or all files. Duplicate filenames have numbered source labels. You can preview
a selected file's extracted text and download it as TXT without any API key.

Choose **Summary** or **Action items** and click **Run document job**. These are
explicit, user-triggered model calls using your existing Groq key or local Ollama;
no new service, key, or paid integration is required. Provider quotas still apply.
The action-items prompt asks for action, owner, deadline and source; missing
owners/dates must be "not specified". It does not create tasks or send messages.
Web search is skipped for document jobs so private document text is not searched.
Regular chat still uses lexical BM25 retrieval from your selected files.

Limits: first 5 files, 2 MB each, first 30 PDF pages, first 120,000 extracted
characters per file. Scanned/empty PDFs are rejected with an OCR hint. Jobs use
whole extracted chunks up to a 14,000-character reference budget. Larger inputs
are sampled across the document, with exact chunk labels and a visible partial
coverage notice. This is not an exhaustive review of long documents. Answers
are short and model-generated; check important claims against the file.

Under **Save your work**, choose any successful answer and download it as
Markdown or TXT, including the source labels, coverage note and web URLs.
Download the whole conversation as Markdown too. Error replies aren't offered
as saved answers. Exports need no key, are generated in-session, and never share
or send a file to anyone. Markdown is the first document format; PDF/Word export,
full URL reading, account actions, autonomous tasks and external sends are left
for later. The original art, persona and controls drawer are unchanged.

`workbench.py` owns bounded job contexts and exports. `test_workbench.py` covers
coverage, chunk labels, export fidelity and a mocked document-job UI flow.
Offline tests do not prove live Groq responses. To run all UI smoke tests locally,
install `requirements.txt` before `python -m unittest discover -v`.

### Search diagnostics and honest resume feedback

Use **Search test query** and **Test web search** in the popover to test your own
wording without an API key. It shows actual source links and any low-relevance
warning. The model is explicitly told when results were already fetched, and
that it sees snippets only. Finding a resume-checker website does not submit
your uploaded resume there. The app has no third-party scoring integration;
any in-app resume score must be labelled an independent estimate with a rubric,
not a real ATS or external service score. Chat cards now use opaque backgrounds
and no text shadow for readable answers over the artwork.
