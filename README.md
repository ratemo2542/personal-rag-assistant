# Personal RAG Assistant

A local-first assistant for asking questions about your own documents. It is designed to retrieve relevant passages before generating an answer, and to show the sources used.

> **Status: early development.** Document ingestion, local embeddings, SQLite retrieval, Ollama answer generation, and a React interface are implemented. Authentication, multi-user isolation, hardened deployment, and production hosting are still in progress. Do not expose this service publicly.

## Current architecture

- **Frontend:** React + Vite
- **API:** Python + FastAPI
- **Document parsing:** PyMuPDF for PDFs; python-docx for DOCX; plain text and Markdown
- **Chunking and embeddings:** Sentence Transformers
- **Vector search and metadata:** SQLite with cosine-similarity ranking
- **Generation:** Ollama for local inference, with a provider interface so a hosted model can be added later

## Development phases

1. API foundation, document parsing, chunking, local embeddings, and SQLite retrieval.
2. Source-grounded answer generation through local Ollama.
3. React document upload and chat interface.
4. Expand integration and security testing.
5. Add authentication, multi-user isolation, observability, and production deployment hardening.

## Initial setup

Requirements: Python 3.11 or newer, Node.js 22 or newer, and Ollama for local answer generation.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

In a second terminal, start the web interface:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite address printed in the terminal (normally `http://127.0.0.1:5173`). Start Ollama separately and pull the configured model before asking questions with `ollama pull llama3.2:3b`.

The API will be available at `http://127.0.0.1:8000`; interactive API documentation is at `/docs`.

- `POST /documents/preview` extracts a safe text preview without saving it.
- `POST /documents/ingest` extracts, chunks, embeds, and saves a document.
- `POST /search` returns the closest stored passages with source filenames and chunk indexes.
- `POST /ask` generates an answer from relevant retrieved passages through local Ollama and returns the supporting sources.
- `GET /health` checks API availability.

To enable local semantic embeddings, install the optional model dependencies with:

```bash
python -m pip install -e ".[embeddings]"
```

The first embedding run downloads the configured Sentence Transformers model. The SQLite store persists document metadata, chunk text, and vectors in a local database file; protect that file like any other personal document store. Search uses cosine ranking over stored vectors. Answer generation requires Ollama to be installed and running locally, with the configured model pulled. The model is instructed to treat retrieved document text as untrusted reference material rather than executable instructions.

## Quality and security principles

- Treat uploaded documents as untrusted input.
- Enforce file type and size limits; never trust a filename or client-supplied MIME type alone.
- Keep secrets out of source control and provide configuration through environment variables.
- The development API allows browser requests only from the configured local frontend origins.
- Do not claim an answer is supported unless retrieved source passages are available.
- Test failure paths as well as successful requests.
- Do not expose this development API publicly without authentication, upload isolation, and deployment hardening.

## License

MIT. See [LICENSE](LICENSE).