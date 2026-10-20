import { useEffect, useRef, useState } from "react";
import { LogOut, Cpu, Boxes, ChevronsUpDown, MessageSquare, FolderGit2 } from "lucide-react";
import { useAuth } from "../AuthContext.jsx";
import { initials, monthYear } from "../util.js";

export default function ProfileMenu({ me, engine }) {
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const email = me?.email || "";

  return (
    <div className="profile" ref={ref}>
      {open && (
        <div className="profile-pop" role="menu">
          <div className="profile-head">
            <span className="avatar-lg">{initials(email)}</span>
            <div className="profile-id">
              <div className="profile-email" title={email}>{email || "…"}</div>
              {me?.member_since && <div className="profile-since">Member since {monthYear(me.member_since)}</div>}
            </div>
          </div>
          <div className="profile-stats">
            <div><MessageSquare size={14} /><b>{me?.n_chats ?? "–"}</b> chats</div>
            <div><FolderGit2 size={14} /><b>{me?.n_repos ?? "–"}</b> repos</div>
          </div>
          {engine && (
            <div className="profile-engine">
              <div className="mini-label">Engine</div>
              <div className="engine-row"><Cpu size={14} /><span>LLM</span><code>{engine.model}</code></div>
              <div className="engine-row"><Boxes size={14} /><span>Retriever</span><code>{engine.retriever}</code></div>
            </div>
          )}
          <button className="profile-logout" onClick={logout} role="menuitem">
            <LogOut size={15} /> Log out
          </button>
        </div>
      )}
      <button className={"profile-btn" + (open ? " open" : "")} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="avatar-sm">{initials(email)}</span>
        <span className="profile-btn-text">
          <span className="profile-btn-name">{me?.name || "Account"}</span>
          <span className="profile-btn-email">{email}</span>
        </span>
        <ChevronsUpDown size={15} />
      </button>
    </div>
  );
}
