import { useEffect, useRef, useState } from "react";
import { MessageSquare, Pencil, Trash2, Check, X } from "lucide-react";
import { groupChats, shortSource } from "../util.js";

export default function ChatList({ chats, activeId, onOpen, onRename, onDelete }) {
  const groups = groupChats(chats);
  return (
    <section className="panel chats-panel">
      <div className="panel-label">Chats</div>
      {chats.length === 0 ? (
        <div className="chats-empty">Your chats will appear here.</div>
      ) : (
        <div className="chat-groups">
          {groups.map((g) => (
            <div key={g.label} className="chat-group">
              <div className="mini-label">{g.label}</div>
              {g.items.map((c) => (
                <ChatItem
                  key={c.id}
                  chat={c}
                  active={c.id === activeId}
                  onOpen={onOpen}
                  onRename={onRename}
                  onDelete={onDelete}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ChatItem({ chat, active, onOpen, onRename, onDelete }) {
  const [mode, setMode] = useState("view"); // view | rename | confirm
  const [title, setTitle] = useState(chat.title);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (mode === "rename") inputRef.current?.select();
  }, [mode]);

  async function saveTitle(e) {
    e?.preventDefault();
    const t = title.trim();
    if (!t || t === chat.title) return setMode("view");
    setBusy(true);
    try {
      await onRename(chat.id, t);
      setMode("view");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    setBusy(true);
    try {
      await onDelete(chat.id);
    } finally {
      setBusy(false);
    }
  }

  if (mode === "rename") {
    return (
      <form className="chat-item editing" onSubmit={saveTitle}>
        <input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setMode("view")}
          disabled={busy}
          aria-label="Chat title"
        />
        <button type="submit" className="icon-btn tiny" aria-label="Save title"><Check size={14} /></button>
        <button type="button" className="icon-btn tiny" onClick={() => setMode("view")} aria-label="Cancel">
          <X size={14} />
        </button>
      </form>
    );
  }

  if (mode === "confirm") {
    return (
      <div className="chat-item confirming">
        <span className="confirm-text">Delete this chat?</span>
        <button className="btn-danger" onClick={confirmDelete} disabled={busy}>Delete</button>
        <button className="icon-btn tiny" onClick={() => setMode("view")} aria-label="Cancel">
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className={"chat-item" + (active ? " active" : "")}>
      <button className="chat-item-main" onClick={() => onOpen(chat.id)} title={chat.title}>
        <MessageSquare size={14} />
        <span className="chat-item-text">
          <span className="chat-item-title">{chat.title}</span>
          {chat.repo && <span className="chat-item-repo">{shortSource(chat.repo)}</span>}
        </span>
      </button>
      <div className="chat-item-actions">
        <button className="icon-btn tiny" onClick={() => { setTitle(chat.title); setMode("rename"); }} aria-label="Rename chat">
          <Pencil size={13} />
        </button>
        <button className="icon-btn tiny" onClick={() => setMode("confirm")} aria-label="Delete chat">
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}
