import { Sparkles, Github, MessageSquare, FileCode2, Layers } from "lucide-react";
import { Ring } from "./Loaders.jsx";
import { displayName, greeting, shortSource, timeAgo } from "../util.js";

const EXAMPLES = [
  { source: "https://github.com/pallets/itsdangerous", note: "small · signing data" },
  { source: "https://github.com/pallets/markupsafe", note: "tiny · HTML escaping" },
  { source: "https://github.com/pallets-eco/blinker", note: "tiny · signals" },
];

function starters(repo) {
  const name = repo.split("/").pop();
  return [
    `What does ${name} do, in simple words?`,
    "Where is the main entry point?",
    "Explain the main data flow step by step.",
    "How is error handling done?",
    "Which files should I read first?",
    "How are the tests organized?",
  ];
}

export default function Welcome({
  me, index, statusLoaded, ingesting, onPick, onIngest, recentChats, onOpenChat,
}) {
  const name = displayName(me?.name || me?.email);
  return (
    <div className="welcome">
      <div className="welcome-badge">
        <Sparkles size={14} /> Codebase RAG
      </div>
      <h1>
        {greeting()}, <span className="accent">{name}</span>
      </h1>

      {!statusLoaded ? null : index ? (
        <>
          <p className="welcome-sub">
            Ask anything about <b>{shortSource(index.source)}</b>. Every answer points to the exact{" "}
            <code>file:line</code> it came from.
          </p>
          <div className="repo-facts">
            <span><Github size={14} /> {shortSource(index.source)}</span>
            <span><FileCode2 size={14} /> {index.n_files} files</span>
            <span><Layers size={14} /> {index.n_chunks} chunks</span>
          </div>
          {ingesting && (
            <div className="welcome-indexing">
              <Ring size={28} /> Indexing {shortSource(ingesting)}… you can ask once it's done.
            </div>
          )}
          <div className="starters">
            {starters(shortSource(index.source)).map((s) => (
              <button key={s} onClick={() => onPick(s)} disabled={Boolean(ingesting)}>
                {s}
              </button>
            ))}
          </div>
          {recentChats.length > 0 && (
            <div className="recent">
              <div className="mini-label">Pick up where you left off</div>
              {recentChats.map((c) => (
                <button key={c.id} className="recent-item" onClick={() => onOpenChat(c.id)}>
                  <MessageSquare size={14} />
                  <span className="recent-title">{c.title}</span>
                  <span className="recent-meta">{timeAgo(c.updated_at)}</span>
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          <p className="welcome-sub">
            Let's get you started. Index a public GitHub repo, then ask questions about its code in
            plain English.
          </p>
          <ol className="steps">
            <li><b>Pick a repo</b> — paste a GitHub link in the sidebar, or try one below.</li>
            <li><b>Wait for indexing</b> — RepoSage reads and splits the code (a few minutes).</li>
            <li><b>Ask away</b> — answers cite the exact files and lines.</li>
          </ol>
          {ingesting ? (
            <div className="welcome-indexing">
              <Ring size={34} /> Indexing {shortSource(ingesting)}…
            </div>
          ) : (
            <div className="examples">
              {EXAMPLES.map((ex) => (
                <button key={ex.source} onClick={() => onIngest(ex.source)}>
                  <Github size={15} />
                  <span className="ex-name">{shortSource(ex.source)}</span>
                  <span className="ex-note">{ex.note}</span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
