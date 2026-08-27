import { useEffect, useRef, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ArrowUp, Sparkles, LogOut } from "lucide-react";
import Sidebar from "./components/Sidebar.jsx";
import Message from "./components/Message.jsx";
import { Dots } from "./components/Loaders.jsx";
import { getStatus, ingestRepo, askQuestion } from "./api.js";
import { useAuth } from "./AuthContext.jsx";
import Login from "./Login.jsx";

const STARTERS = [
  "What does this project do?",
  "Where is the entry point?",
  "How is authentication handled?",
  "Explain the main data flow.",
];

export default function App() {
  const { isAuthenticated } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
      <Route path="/" element={isAuthenticated ? <ChatApp /> : <Navigate to="/login" />} />
    </Routes>
  );
}

function ChatApp() {
  const { logout } = useAuth();
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [ingesting, setIngesting] = useState(false);
  const [ingestError, setIngestError] = useState("");
  const [agentic, setAgentic] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  const scrollRef = useRef(null);
  const anchorRef = useRef(null);
  const taRef = useRef(null);
  const indexed = Boolean(status?.index);
  const lastUserIndex = messages.map((m) => m.role).lastIndexOf("user");

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    const el = taRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 200) + "px";
    }
  }, [question]);

  useEffect(() => {
    if (anchorRef.current) {
      anchorRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length]);

  async function handleIngest(source) {
    setIngesting(true);
    setIngestError("");
    try {
      const res = await ingestRepo(source);
      setStatus((s) => ({ ...s, index: res.index }));
      setMessages([]);
    } catch (e) {
      setIngestError(e.message);
    } finally {
      setIngesting(false);
    }
  }

  async function submit(text) {
    const q = text.trim();
    if (!q || asking || !indexed) return;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setAsking(true);
    try {
      const res = await askQuestion(q, agentic);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.text, sources: res.sources, trace: res.trace },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: e.message, error: true }]);
    } finally {
      setAsking(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(question);
    }
  }

  return (
    <div className="app">
      <Sidebar
        status={status}
        ingesting={ingesting}
        ingestError={ingestError}
        onIngest={handleIngest}
        agentic={agentic}
        setAgentic={setAgentic}
        onClear={() => setMessages([])}
        hasMessages={messages.length > 0}
      >
        <div style={{ marginTop: 'auto', padding: '10px' }}>
          <button onClick={logout} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </Sidebar>

      <main className="chat">
        <div className="chat-scroll" ref={scrollRef}>
          <div className="chat-inner">
            {messages.length === 0 ? (
              <Welcome
                indexed={indexed}
                source={status?.index?.source}
                onPick={submit}
              />
            ) : (
              messages.map((m, i) => (
                <div
                  key={i}
                  ref={i === lastUserIndex ? anchorRef : null}
                  className={i === lastUserIndex ? "turn-anchor" : undefined}
                >
                  <Message msg={m} />
                </div>
              ))
            )}
            {asking && (
              <div className="thinking">
                <span className="thinking-avatar">
                  <Sparkles size={15} />
                </span>
                <Dots />
                <span className="thinking-label">
                  {agentic ? "retrieving · grading · answering" : "searching the codebase"}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <textarea
              ref={taRef}
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={indexed ? "Ask anything about this codebase…" : "Index a repository to start chatting"}
              disabled={!indexed || asking}
            />
            <button
              className="send"
              onClick={() => submit(question)}
              disabled={!indexed || asking || !question.trim()}
              aria-label="Send"
            >
              <ArrowUp size={18} />
            </button>
          </div>
          <p className="composer-hint">
            Answers are grounded in the indexed code with <code>file:line</code> citations.
          </p>
        </div>
      </main>
    </div>
  );
}

function Welcome({ indexed, source, onPick }) {
  return (
    <div className="welcome">
      <div className="welcome-badge">
        <Sparkles size={14} /> Codebase RAG
      </div>
      <h1>
        Chat with a <span className="accent">Codebase</span>
      </h1>
      <p className="welcome-sub">
        {indexed ? (
          <>
            Indexed <b>{shortSource(source)}</b>. Ask a question below and get answers
            grounded in the real source, with clickable <code>file:line</code> citations.
          </>
        ) : (
          <>Point it at any GitHub repo from the panel on the left, then ask away.</>
        )}
      </p>
      {indexed && (
        <div className="starters">
          {STARTERS.map((s) => (
            <button key={s} onClick={() => onPick(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function shortSource(source) {
  if (!source) return "the repository";
  return source.replace(/\.git$/, "").split("/").slice(-2).join("/");
}
