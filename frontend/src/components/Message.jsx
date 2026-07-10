import { Sparkles, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import Sources from "./Sources.jsx";

export default function Message({ msg }) {
  if (msg.role === "user") {
    return (
      <div className="row user">
        <div className="bubble-user">{msg.content}</div>
      </div>
    );
  }

  const rewrites = msg.trace?.rewrites;
  return (
    <div className="row assistant">
      <span className="avatar">
        <Sparkles size={15} />
      </span>
      <div className="assistant-body">
        {rewrites > 0 && (
          <div className="trace">
            <RefreshCw size={12} /> agent rewrote the query {rewrites}×
          </div>
        )}
        <div className={"markdown" + (msg.error ? " error" : "")}>
          {msg.error ? (
            msg.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {msg.content}
            </ReactMarkdown>
          )}
        </div>
        {msg.sources?.length > 0 && <Sources sources={msg.sources} />}
      </div>
    </div>
  );
}
