# PlacidWay Website Knowledge Chatbot

A chatbot that answers visitor questions using only 7 shared PlacidWay pages. Every answer cites its source URL. If the answer is not in the pages, the bot says so.

**Live demo:** (add the URL after deployment)

## Features
- Answers only from the 7 given pages (no crawling beyond them)
- Source links under every answer
- Honest "not in the content" answers, with a pointer to a free quote
- Prices shown with currency and the page's wording
- Refuses weather, booking and medical advice; does not accept wrong prices
- Follow-up questions use chat history
- Replies in the user's language (tested with Urdu)
- Refresh button to re-read the pages
- Lead capture (name and email, with consent)
- Log of unanswered questions

## Architecture
1. `scrape.py` downloads the 7 pages. It checks robots.txt, uses a clear User-Agent, and waits 1 second between requests. Tables are read separately so prices stay next to their names.
2. `ingest.py` cleans the text and splits it into chunks. Each section keeps its heading, and table rows stay together. Chunks are saved in ChromaDB.
3. `retriever.py` searches by meaning (vectors) and by exact keywords, drops chunks that are too far from the question, and returns text with URLs.
4. `rag_chain.py` rewrites the question into a standalone English search query using the chat history, retrieves chunks, and asks the LLM to answer with a strict prompt.
5. `app.py` is the Streamlit chat interface.

## Tools and models, and why
- **Python, LangChain, ChromaDB:** simple, well known, runs locally.
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`. Free, small, and supports Urdu and Arabic questions against English pages.
- **LLM:** Groq `openai/gpt-oss-120b`. Free tier, fast, writes Urdu and Arabic.
- **Streamlit:** quick chat UI and easy free hosting.

## Design choices
- **Small chunks (600 characters):** the embedding model reads only about 128 tokens, so longer chunks are partly invisible to search.
- **Cosine distance with a threshold of 0.75:** removes clearly unrelated chunks. The final "I don't know" decision is made by the prompt, because scores for in-scope and out-of-scope questions overlap.
- **Hybrid search:** keywords find rows (such as the clinic price table) that the embedding model misses.
- **Query rewrite:** turns follow-ups and Roman Urdu into a clear English query.
- **Low temperature (0):** keeps answers stable.

## Setup
1. Install Python 3.11+ and `uv` (or use pip).
2. Clone the repo and install:pip install -r requirements.txt
   or `python -m uv sync`.
3. Copy `.env.example` to `.env` and add your free key from console.groq.com:GROQ_API_KEY=your_key_here4.
4. Build the index (the app also does this on first start):python scrape.py
python ingest.py
5. Run:streamlit run app.py

## Refreshing content
Click **Refresh content** in the sidebar. It re-downloads the 7 pages, rebuilds the index and reloads it.

## Test results
The answers to the 8 test questions (plus Urdu and Roman Urdu) are in `results/test_chain.txt`.

## Project layout
app.py chat interface
scrape.py downloads the 7 pages
ingest.py chunking and indexing
retriever.py vector + keyword search
rag_chain.py prompt and answer logic
data/raw/ scraped pages (JSON)
results/ test answers
tools/ test and debug scripts

## Known limits
- Only the 7 shared pages are used.
- Free Groq limit is about 8,000 tokens per minute, so many fast questions can get a "busy" message.
- Price data can be old. Page 7 shows modified dates, and the bot repeats them.
- Anyone can press Refresh. Lead and log files may be lost when a free host restarts.

