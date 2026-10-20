import { MessageSquareCode, Plus, X } from "lucide-react";
import RepoPanel from "./RepoPanel.jsx";
import ChatList from "./ChatList.jsx";
import ProfileMenu from "./ProfileMenu.jsx";

export default function Sidebar({
  me, status, chats, repos, activeChatId, ingesting, ingestError,
  onIngest, onForgetRepo, onNewChat, onOpenChat, onRenameChat, onDeleteChat, onClose,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="brand">
          <span className="brand-mark">
            <MessageSquareCode size={18} />
          </span>
          <div>
            <div className="brand-name">RepoSage</div>
            <div className="brand-tag">grounded answers over any repo</div>
          </div>
        </div>
        <button className="icon-btn close-btn" onClick={onClose} aria-label="Close menu">
          <X size={18} />
        </button>
      </div>

      <button className="btn-new-chat" onClick={onNewChat}>
        <Plus size={16} /> New chat
      </button>

      <RepoPanel
        index={status?.index}
        repos={repos}
        ingesting={ingesting}
        ingestError={ingestError}
        onIngest={onIngest}
        onForget={onForgetRepo}
      />

      <ChatList
        chats={chats}
        activeId={activeChatId}
        onOpen={onOpenChat}
        onRename={onRenameChat}
        onDelete={onDeleteChat}
      />

      <ProfileMenu me={me} engine={status?.engine} />
    </aside>
  );
}
