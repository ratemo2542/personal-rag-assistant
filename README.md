# Personal RAG Assistant

A local-first assistant for asking questions about your own documents. It is designed to retrieve relevant passages before generating an answer, and to show the sources used.

> **Status: early development.** The API foundation, document preview, chunking, SQLite vector persistence, and a lazy local embedding adapter are implemented. End-to-end ingestion, answer generation, authentication, hardened upload isolation, and the web interface are still in progress. Do not expose this service publicly.

## Planned architecture

- **Frontend:** React + Vite
- **API:** Python + FastAPI
- **Document parsing:** PyMuPDF for PDFs; python-docx for DOCX; plain text and Markdown
- **Chunking and embeddings:** Sentence Transformers
- **Vector search:** ChromaDB
- **Metadata:** SQLite
- **Generation:** Ollama for local inference, with a provider interface so a hosted model can be added later

## Development phases

1. Build and test the API foundation.
2. Validate and extract uploaded documents.
3. Split documents, generate local embeddings, and persist them in SQLite.
4. Retrieve relevant passages through the `/search` endpoint with document and chunk references.
5. Add grounded answer generation through a local Ollama model.
6. Add the React chat and document-management interface.
7. Add authentication, security hardening, observability, and deployment documentation.

## Initial setup

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`; interactive API documentation is at `/docs`.\n\n- `POST /documents/preview` extracts a safe text preview without saving it.\n- `POST /documents/ingest` extracts, chunks, embeds, and saves a document.\n- `POST /search` returns the closest stored passages with source filenames and chunk indexes.\n- `GET /health` checks API availability.\n\nTo enable local semantic embeddings, install the optional model dependencies with:\n\n```bash\npython -m pip install -e ".[embeddings]"\n```\n\nThe first embedding run downloads the configured Sentence Transformers model. The SQLite store persists document metadata, chunk text, and vectors in a local database file; protect that file like any other personal document store. Search is exact cosine ranking over the stored vectors; it does not generate a natural-language answer yet.

## Quality and security principles

- Treat uploaded documents as untrusted input.
- Enforce file type and size limits; never trust a filename or client-supplied MIME type alone.
- Keep secrets out of source control and provide configuration through environment variables.
- Do not claim an answer is supported unless retrieved source passages are available.
- Test failure paths as well as successful requests.
- Do not expose this development API publicly without authentication, upload isolation, and deployment hardening.

## License

License to be selected before public reuse.