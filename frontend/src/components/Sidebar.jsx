import { useState } from "react";
import { Github, Trash2, Cpu, Boxes, MessageSquareCode } from "lucide-react";
import { Ring } from "./Loaders.jsx";

export default function Sidebar({
  status,
  ingesting,
  ingestError,
  onIngest,
  agentic,
  setAgentic,
  onClear,
  hasMessages,
}) {
  const [source, setSource] = useState("");
  const index = status?.index;
  const engine = status?.engine;

  function submit(e) {
    e.preventDefault();
    if (source.trim() && !ingesting) onIngest(source.trim());
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <MessageSquareCode size={18} />
        </span>
        <div>
          <div className="brand-name">RepoSage</div>
          <div className="brand-tag">grounded answers over any repo</div>
        </div>
      </div>

      <section className="panel">
        <div className="panel-label">Repository</div>
        <form onSubmit={submit} className="ingest-form">
          <div className="ingest-field">
            <Github size={16} />
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="github.com/pallets/click"
              disabled={ingesting}
              spellCheck={false}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={ingesting || !source.trim()}>
            {ingesting ? "Indexing…" : "Index repository"}
          </button>
        </form>

        {ingesting && (
          <div className="ingest-loader">
            <Ring />
            <div>
              <div className="ingest-loader-title">Indexing repository</div>
              <div className="ingest-loader-sub">clone → chunk → embed</div>
            </div>
          </div>
        )}

        {ingestError && <div className="alert">{ingestError}</div>}

        {index && !ingesting && (
          <div className="repo-card">
            <div className="repo-card-top">
              <span className="live-dot" />
              <span className="repo-name">{shortSource(index.source)}</span>
            </div>
            <div className="repo-stats">
              <span>{index.n_files} files</span>
              <span>{index.n_chunks} chunks</span>
              <span>{(index.embed_model || "").split("/").pop()}</span>
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-label">Settings</div>
        <label className="toggle-row">
          <div>
            <div className="toggle-title">Agentic mode</div>
            <div className="toggle-sub">grade &amp; rewrite weak retrievals</div>
          </div>
          <button
            type="button"
            className={"switch" + (agentic ? " on" : "")}
            onClick={() => setAgentic((v) => !v)}
            aria-pressed={agentic}
          >
            <span className="knob" />
          </button>
        </label>
        <button className="btn-ghost" onClick={onClear} disabled={!hasMessages}>
          <Trash2 size={15} /> Clear conversation
        </button>
      </section>

      {engine && (
        <section className="panel engine">
          <div className="panel-label">Engine</div>
          <div className="engine-row">
            <Cpu size={14} />
            <span>LLM</span>
            <code>{engine.model}</code>
          </div>
          <div className="engine-row">
            <Boxes size={14} />
            <span>Retriever</span>
            <code>{engine.retriever}</code>
          </div>
        </section>
      )}

      <div className="sidebar-foot">Local embeddings · free LLM · cited answers</div>
    </aside>
  );
}

function shortSource(source) {
  if (!source) return "repository";
  return source.replace(/\.git$/, "").split("/").slice(-2).join("/");
}
