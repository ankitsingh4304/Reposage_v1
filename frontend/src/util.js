export function shortSource(source) {
  if (!source) return "repository";
  return source.replace(/\.git$/, "").split("/").slice(-2).join("/");
}

export function repoUrl(source) {
  return (source || "").replace(/\.git$/, "");
}

export function displayName(nameOrEmail) {
  const base = (nameOrEmail || "").split("@")[0].replace(/[._-]+/g, " ").trim();
  if (!base) return "there";
  const first = base.split(" ")[0];
  return first.charAt(0).toUpperCase() + first.slice(1);
}

export function initials(email) {
  const base = (email || "?").split("@")[0].replace(/[^a-zA-Z0-9]/g, "");
  return (base.slice(0, 2) || "?").toUpperCase();
}

export function greeting(date = new Date()) {
  const h = date.getHours();
  if (h < 5) return "Up late";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// Bucket chats like ChatGPT: Today / Yesterday / Previous 7 days / Older.
export function groupChats(chats, now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 86400000;
  const groups = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Previous 7 days", items: [] },
    { label: "Older", items: [] },
  ];
  for (const c of chats) {
    const t = new Date(c.updated_at || c.created_at || 0).getTime();
    if (t >= start) groups[0].items.push(c);
    else if (t >= start - day) groups[1].items.push(c);
    else if (t >= start - 7 * day) groups[2].items.push(c);
    else groups[3].items.push(c);
  }
  return groups.filter((g) => g.items.length);
}

export function timeAgo(iso) {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function monthYear(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}
