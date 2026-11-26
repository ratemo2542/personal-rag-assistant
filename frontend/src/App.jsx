import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const fileInput = useRef(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [messages, setMessages] = useState([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);

  async function loadDocuments() {
    try {
      const response = await fetch(`${API}/documents`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load documents.");
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message || "Could not load the document library.");
    } finally {
      setLoadingDocuments(false);
    }
  }

  useEffect(() => { loadDocuments(); }, []);

  async function deleteDocument(id) {
    try {
      const response = await fetch(`${API}/documents/${id}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not delete document.");
      await loadDocuments();
    } catch (err) {
      setError(err.message || "Could not delete document.");
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API}/documents/ingest`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Document upload failed.");
      setNotice(`Added ${data.filename} · ${data.chunks} searchable passage(s)`);
      await loadDocuments();
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (err) {
      setError(err.message || "Could not reach the API. Check that the backend is running.");
    } finally {
      setUploading(false);
    }
  }

  async function askQuestion(event) {
    event.preventDefault();
    const prompt = question.trim();
    if (!prompt || asking) return;
    setMessages((current) => [...current, { role: "user", text: prompt }]);
    setQuestion("");
    setAsking(true);
    setError("");
    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: prompt, limit: 5 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "The assistant could not answer.");
      setMessages((current) => [...current, {
        role: "assistant",
        text: data.answer,
        sources: data.sources || [],
      }]);
    } catch (err) {
      setError(err.message || "Could not reach the API.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Personal RAG Assistant home">
          <span className="brand-mark">✳</span>
          <span>PERSONAL <b>RAG</b></span>
        </a>
        <span className="local-pill"><i /> LOCAL WORKSPACE</span>
      </header>

      <section className="intro">
        <p className="eyebrow">YOUR KNOWLEDGE, CONNECTED</p>
        <h1>Ask your documents<br /><span>anything.</span></h1>
        <p className="subhead">Bring your notes, PDFs and documents together. Get answers grounded in the information you already own.</p>
      </section>

      <section className="workspace">
        <aside className="library panel">
          <div className="panel-heading">
            <div><p className="eyebrow">KNOWLEDGE BASE</p><h2>Add a document</h2></div>
            <span className="panel-icon">↥</span>
          </div>
          <p className="muted">Upload a file to make its contents searchable by meaning.</p>
          <form onSubmit={uploadDocument}>
            <label className="dropzone" htmlFor="document-file">
              <span className="upload-icon">＋</span>
              <strong>{file ? file.name : "Choose a document"}</strong>
              <span>{file ? "Ready to add to your library" : "PDF, DOCX, TXT or Markdown"}</span>
              <input
                ref={fileInput}
                id="document-file"
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </label>
            <button className="primary-button full" type="submit" disabled={!file || uploading}>
              {uploading ? "Indexing document…" : "Add to knowledge base"}
            </button>
          </form>
          <div className="privacy-note"><span>◈</span><p><b>Local-first by design</b><br />Your files are processed by your local API and stored in your local database.</p></div>
          <div className="library-list">
            <div className="library-list-heading"><b>Your library</b><span>{documents.length} FILE{documents.length === 1 ? "" : "S"}</span></div>
            {loadingDocuments ? <p className="library-empty">Loading library…</p> : documents.length === 0 ? <p className="library-empty">Your documents will appear here.</p> : documents.map((document) => (
              <div className="library-document" key={document.id}>
                <span className="file-symbol">▤</span>
                <div className="library-document-info"><b>{document.filename}</b><small>{document.chunk_count} searchable passage(s)</small></div>
                <button type="button" className="delete-document" onClick={() => deleteDocument(document.id)} aria-label={`Delete ${document.filename}`}>×</button>
              </div>
            ))}
          </div>
          {notice && <p className="notice" role="status">{notice}</p>}
        </aside>

        <section className="chat panel">
          <div className="panel-heading chat-heading">
            <div><p className="eyebrow">PERSONAL ASSISTANT</p><h2>Knowledge chat</h2></div>
            <span className="online-status"><i /> READY</span>
          </div>
          <div className="conversation" aria-live="polite">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="sparkle">✳</div>
                <h3>Your knowledge, at your fingertips.</h3>
                <p>Add a document, then ask a question. Answers include the source passages used.</p>
                <div className="suggestions">
                  <button type="button" onClick={() => setQuestion("Summarise my uploaded documents.")}>Summarise my documents</button>
                  <button type="button" onClick={() => setQuestion("What are the most important points?")}>Find the key points</button>
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <article className={`message ${message.role}`} key={index}>
                <span className="message-label">{message.role === "user" ? "YOU" : "ASSISTANT"}</span>
                <p>{message.text}</p>
                {message.sources?.length > 0 && (
                  <div className="sources">
                    <span className="sources-title">SOURCES USED</span>
                    {message.sources.map((source, sourceIndex) => (
                      <div className="source" key={`${source.document_id}-${source.chunk_index}-${sourceIndex}`}>
                        <span>↳</span>
                        <div><b>{source.filename}</b><small>Passage {source.chunk_index + 1} · relevance {Math.round(source.score * 100)}%</small></div>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {asking && <div className="typing"><i /><i /><i /><span>Searching your knowledge…</span></div>}
          </div>
          <form className="composer" onSubmit={askQuestion}>
            <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about your documents…" aria-label="Ask a question" />
            <button className="send-button" type="submit" disabled={!question.trim() || asking} aria-label="Send question">↑</button>
          </form>
          <p className="chat-footnote">Answers are generated from retrieved passages. Always verify important details against the sources.</p>
        </section>
      </section>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <footer><span>PERSONAL RAG ASSISTANT</span><span>PRIVATE BY DEFAULT · BUILT FOR YOUR KNOWLEDGE</span></footer>
    </main>
  );
}