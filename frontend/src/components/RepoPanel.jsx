import { useState } from "react";
import { Github, ChevronDown, RotateCw, X, ExternalLink } from "lucide-react";
import { Ring } from "./Loaders.jsx";
import { shortSource, repoUrl, timeAgo } from "../util.js";

export default function RepoPanel({ index, repos, ingesting, ingestError, onIngest, onForget }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const showForm = open || !index;

  async function submit(e) {
    e.preventDefault();
    const s = source.trim();
    if (!s || ingesting) return;
    if (await onIngest(s)) {
      setSource("");
      setOpen(false);
    }
  }

  const others = repos.filter((r) => r.source !== index?.source);

  return (
    <section className="panel repo-panel">
      <div className="panel-label">Repository</div>

      {ingesting ? (
        <div className="ingest-loader">
          <Ring size={36} />
          <div>
            <div className="ingest-loader-title">Indexing {shortSource(ingesting)}</div>
            <div className="ingest-loader-sub">clone → chunk → embed · a few minutes on the free server</div>
          </div>
        </div>
      ) : index ? (
        <button className={"repo-card" + (open ? " open" : "")} onClick={() => setOpen((v) => !v)}>
          <div className="repo-card-top">
            <span className="live-dot" />
            <span className="repo-name">{shortSource(index.source)}</span>
            <ChevronDown size={15} className="chevron" />
          </div>
          <div className="repo-stats">
            <span>{index.n_files} files</span>
            <span>{index.n_chunks} chunks</span>
          </div>
        </button>
      ) : null}

      {ingestError && <div className="alert">{ingestError}</div>}

      {showForm && !ingesting && (
        <div className="repo-drawer">
          <form onSubmit={submit} className="ingest-form">
            <div className="ingest-field">
              <Github size={16} />
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="github.com/owner/repo"
                spellCheck={false}
                aria-label="GitHub repository URL"
              />
            </div>
            <button type="submit" className="btn-primary" disabled={!source.trim()}>
              {index ? "Index this repository" : "Index repository"}
            </button>
          </form>

          {index && (
            <a className="repo-link" href={repoUrl(index.source)} target="_blank" rel="noreferrer">
              <ExternalLink size={13} /> Open {shortSource(index.source)} on GitHub
            </a>
          )}

          {others.length > 0 && (
            <div className="my-repos">
              <div className="mini-label">My repositories</div>
              {others.slice(0, 6).map((r) => (
                <div className="my-repo" key={r.source}>
                  <button
                    className="my-repo-main"
                    onClick={() => onIngest(r.source).then((ok) => ok && setOpen(false))}
                    title={`Re-index ${shortSource(r.source)}`}
                  >
                    <RotateCw size={13} />
                    <span className="my-repo-name">{shortSource(r.source)}</span>
                    <span className="my-repo-meta">{timeAgo(r.last_indexed_at)}</span>
                  </button>
                  <button
                    className="icon-btn tiny"
                    onClick={() => onForget(r.source)}
                    aria-label={`Remove ${shortSource(r.source)} from the list`}
                    title="Remove from list"
                  >
                    <X size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
