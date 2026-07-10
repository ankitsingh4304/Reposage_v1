import { useState } from "react";
import { ChevronRight, FileCode2 } from "lucide-react";

export default function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={"sources" + (open ? " open" : "")}>
      <button className="sources-head" onClick={() => setOpen((v) => !v)}>
        <ChevronRight size={15} className="chevron" />
        <FileCode2 size={15} />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""}</span>
      </button>
      {open && (
        <div className="sources-list">
          {sources.map((s, i) => (
            <div className="source" key={i}>
              <div className="source-head">
                <code className="citation">{s.citation}</code>
                <span className="score">{s.score.toFixed(2)}</span>
              </div>
              <pre className="snippet">
                <code>{s.text}</code>
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
