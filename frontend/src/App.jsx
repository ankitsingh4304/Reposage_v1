import { useCallback, useEffect, useRef, useState } from "react";
import { Routes, Route, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowUp, Sparkles, Menu, AlertTriangle, RefreshCw, Bot } from "lucide-react";
import Sidebar from "./components/Sidebar.jsx";
import Message from "./components/Message.jsx";
import Welcome from "./components/Welcome.jsx";
import { Dots } from "./components/Loaders.jsx";
import {
  getStatus, getMe, listChats, listRepos, getChat, ingestRepo, askQuestion,
  renameChat, deleteChat, forgetRepo,
} from "./api.js";
import { useAuth } from "./AuthContext.jsx";
import Login from "./Login.jsx";
import { shortSource } from "./util.js";

export default function App() {
  const { isAuthenticated } = useAuth();
  const protectedEl = isAuthenticated ? <ChatApp /> : <Navigate to="/login" replace />;
  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" replace />} />
      <Route path="/" element={protectedEl} />
      <Route path="/c/:chatId" element={protectedEl} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function ChatApp() {
  const { chatId } = useParams();
  const navigate = useNavigate();

  const [me, setMe] = useState(null);
  const [status, setStatus] = useState(null);
  const [chats, setChats] = useState([]);
  const [repos, setRepos] = useState([]);
  const [chat, setChat] = useState(null); // {id, title, repo} of the open chat
  const [messages, setMessages] = useState([]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [chatError, setChatError] = useState("");

  const [ingesting, setIngesting] = useState(null); // source being indexed
  const [ingestError, setIngestError] = useState("");
  const [agentic, setAgentic] = useState(() => localStorage.getItem("agentic") === "1");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [waking, setWaking] = useState(false);

  const scrollRef = useRef(null);
  const anchorRef = useRef(null);
  const taRef = useRef(null);
  const skipLoadRef = useRef(null); // chat id we just created; its messages are already on screen

  const index = status?.index;
  const indexed = Boolean(index);
  const repoMismatch = Boolean(chat?.repo && index?.source && chat.repo !== index.source);
  const canAsk = indexed && !asking && !ingesting && !repoMismatch;
  const lastUserIndex = messages.map((m) => m.role).lastIndexOf("user");

  // ---- initial data ----
  const refreshLists = useCallback(() => {
    listChats().then(setChats).catch(() => {});
    listRepos().then(setRepos).catch(() => {});
    getMe().then(setMe).catch(() => {});
  }, []);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
    refreshLists();
  }, [refreshLists]);

  useEffect(() => {
    const onSlow = (e) => setWaking(Boolean(e.detail));
    window.addEventListener("api-slow", onSlow);
    return () => window.removeEventListener("api-slow", onSlow);
  }, []);

  useEffect(() => {
    try { localStorage.setItem("agentic", agentic ? "1" : "0"); } catch { /* ignore */ }
  }, [agentic]);

  // ---- open a chat when the URL changes ----
  useEffect(() => {
    setSidebarOpen(false);
    setChatError("");
    if (!chatId) {
      setChat(null);
      setMessages([]);
      return;
    }
    if (skipLoadRef.current === chatId) {
      skipLoadRef.current = null;
      return;
    }
    let cancelled = false;
    setLoadingChat(true);
    getChat(chatId)
      .then((c) => {
        if (cancelled) return;
        setChat({ id: c.id, title: c.title, repo: c.repo });
        setMessages(c.messages);
      })
      .catch((e) => {
        if (cancelled) return;
        setChat(null);
        setMessages([]);
        setChatError(e.message);
      })
      .finally(() => !cancelled && setLoadingChat(false));
    return () => { cancelled = true; };
  }, [chatId]);

  // ---- composer autosize + scroll ----
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
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    }
  }, [messages.length]);

  // ---- actions ----
  async function handleIngest(source, { startNewChat = true } = {}) {
    setIngesting(source);
    setIngestError("");
    try {
      const res = await ingestRepo(source);
      setStatus((s) => ({ ...s, index: res.index }));
      refreshLists();
      if (startNewChat) navigate("/");
      return true;
    } catch (e) {
      setIngestError(e.message);
      return false;
    } finally {
      setIngesting(null);
    }
  }

  async function submit(text) {
    const q = text.trim();
    if (!q || !canAsk) return;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setAsking(true);
    try {
      const res = await askQuestion(q, agentic, chat?.id);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.text, sources: res.sources, trace: res.trace },
      ]);
      const conv = res.conversation;
      if (conv && conv.id !== chat?.id) {
        skipLoadRef.current = conv.id;
        setChat({ id: conv.id, title: conv.title, repo: conv.repo });
        navigate(`/c/${conv.id}`, { replace: !chat });
      }
      if (conv) {
        setChats((list) => [conv, ...list.filter((c) => c.id !== conv.id)]);
        if (!chat) getMe().then(setMe).catch(() => {});
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: e.message, error: true }]);
    } finally {
      setAsking(false);
    }
  }

  async function handleRename(id, title) {
    const updated = await renameChat(id, title);
    setChats((list) => list.map((c) => (c.id === id ? { ...c, title: updated.title } : c)));
    if (chat?.id === id) setChat((c) => ({ ...c, title: updated.title }));
  }

  async function handleDelete(id) {
    await deleteChat(id);
    setChats((list) => list.filter((c) => c.id !== id));
    getMe().then(setMe).catch(() => {});
    if (chat?.id === id) navigate("/");
  }

  async function handleForgetRepo(source) {
    await forgetRepo(source);
    setRepos((list) => list.filter((r) => r.source !== source));
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(question);
    }
  }

  const placeholder = !indexed
    ? "Index a repository to start chatting"
    : repoMismatch
      ? "Re-index this chat's repository to continue"
      : chat
        ? "Ask a follow-up…"
        : `Ask anything about ${shortSource(index.source)}…`;

  return (
    <div className={"app" + (sidebarOpen ? " sidebar-open" : "")}>
      <Sidebar
        me={me}
        status={status}
        chats={chats}
        repos={repos}
        activeChatId={chat?.id}
        ingesting={ingesting}
        ingestError={ingestError}
        onIngest={handleIngest}
        onForgetRepo={handleForgetRepo}
        onNewChat={() => navigate("/")}
        onOpenChat={(id) => navigate(`/c/${id}`)}
        onRenameChat={handleRename}
        onDeleteChat={handleDelete}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="scrim" onClick={() => setSidebarOpen(false)} />

      <main className="chat">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            <Menu size={18} />
          </button>
          <div className="topbar-title">{chat?.title || "New chat"}</div>
          {(chat?.repo || index?.source) && (
            <span className={"repo-chip" + (repoMismatch ? " warn" : "")} title={chat?.repo || index?.source}>
              {shortSource(chat?.repo || index?.source)}
            </span>
          )}
        </header>

        {waking && (
          <div className="waking">
            <Dots /> Waking up the server… on the free plan this can take up to a minute.
          </div>
        )}

        <div className="chat-scroll" ref={scrollRef}>
          <div className="chat-inner">
            {loadingChat ? (
              <div className="chat-loading"><Dots /> Loading chat…</div>
            ) : chatError ? (
              <div className="empty-note">
                <AlertTriangle size={18} /> {chatError}
              </div>
            ) : messages.length === 0 ? (
              <Welcome
                me={me}
                index={index}
                statusLoaded={status !== null}
                ingesting={ingesting}
                onPick={submit}
                onIngest={handleIngest}
                recentChats={chats.slice(0, 3)}
                onOpenChat={(id) => navigate(`/c/${id}`)}
              />
            ) : (
              messages.map((m, i) => (
                <div
                  key={m.id || i}
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
          {repoMismatch && (
            <div className="mismatch">
              <AlertTriangle size={16} />
              <span>
                This chat is about <b>{shortSource(chat.repo)}</b>, but your current index is{" "}
                <b>{shortSource(index.source)}</b>.
              </span>
              <button
                className="btn-small"
                disabled={Boolean(ingesting)}
                onClick={() => handleIngest(chat.repo, { startNewChat: false })}
              >
                <RefreshCw size={13} /> {ingesting ? "Indexing…" : "Re-index"}
              </button>
            </div>
          )}
          <div className={"composer" + (canAsk ? "" : " disabled")}>
            <textarea
              ref={taRef}
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              disabled={!canAsk}
            />
            <button
              className="send"
              onClick={() => submit(question)}
              disabled={!canAsk || !question.trim()}
              aria-label="Send"
            >
              <ArrowUp size={18} />
            </button>
          </div>
          <div className="composer-foot">
            <button
              type="button"
              className={"agent-toggle" + (agentic ? " on" : "")}
              onClick={() => setAgentic((v) => !v)}
              aria-pressed={agentic}
              title="Grades the retrieved code and rewrites the search if it's weak. Slower, often better."
            >
              <Bot size={14} /> Agent mode {agentic ? "on" : "off"}
            </button>
            <span className="composer-hint">
              Answers cite the code as <code>file:line</code>
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
