import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquareCode, Mail, Lock, Eye, EyeOff, FileCode2, Bot, History, AlertCircle,
} from "lucide-react";
import { useAuth } from "./AuthContext";
import { Dots } from "./components/Loaders.jsx";

const FEATURES = [
  { icon: FileCode2, title: "Answers with receipts", text: "Every claim links to the exact file and line." },
  { icon: Bot, title: "Agent mode", text: "Grades its own search and retries when results are weak." },
  { icon: History, title: "Your chats, saved", text: "Pick up any conversation where you left it." },
];

export default function Login() {
  const [mode, setMode] = useState("login"); // login | register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const isRegister = mode === "register";

  useEffect(() => {
    const onSlow = (e) => setWaking(Boolean(e.detail));
    window.addEventListener("api-slow", onSlow);
    return () => window.removeEventListener("api-slow", onSlow);
  }, []);

  function switchMode(next) {
    setMode(next);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (isRegister && password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      if (isRegister) await register(email.trim(), password);
      else await login(email.trim(), password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth-hero">
        <div className="brand">
          <span className="brand-mark">
            <MessageSquareCode size={18} />
          </span>
          <div className="brand-name">RepoSage</div>
        </div>
        <h1>
          Ask any GitHub repo.<br />
          Get answers with <span className="accent">file:line</span> proof.
        </h1>
        <p className="auth-lead">
          Paste a repository link, and RepoSage reads the code so you can ask questions in plain
          English.
        </p>
        <ul className="auth-features">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <li key={title}>
              <span className="feature-icon"><Icon size={16} /></span>
              <div>
                <div className="feature-title">{title}</div>
                <div className="feature-text">{text}</div>
              </div>
            </li>
          ))}
        </ul>
        <div className="auth-sample" aria-hidden="true">
          <div className="sample-q">Where is the signature checked?</div>
          <div className="sample-a">
            <code>Signer.verify_signature</code> tries each secret key, and the digest is
            compared with <code>hmac.compare_digest</code>{" "}
            <code className="citation">src/itsdangerous/signer.py:227-242</code>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>
          <p className="auth-sub">
            {isRegister ? "It's free. You only need an email." : "Log in to see your chats and repos."}
          </p>

          <div className="seg" role="tablist">
            <button type="button" role="tab" aria-selected={!isRegister}
              className={!isRegister ? "on" : ""} onClick={() => switchMode("login")}>Log in</button>
            <button type="button" role="tab" aria-selected={isRegister}
              className={isRegister ? "on" : ""} onClick={() => switchMode("register")}>Sign up</button>
          </div>

          <label className="field">
            <span className="field-label">Email</span>
            <span className="field-box">
              <Mail size={16} />
              <input
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </span>
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <span className="field-box">
              <Lock size={16} />
              <input
                type={showPw ? "text" : "password"}
                autoComplete={isRegister ? "new-password" : "current-password"}
                placeholder={isRegister ? "At least 6 characters" : "Your password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="icon-btn tiny"
                onClick={() => setShowPw((v) => !v)}
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </span>
          </label>

          {error && (
            <div className="auth-error" role="alert">
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <button type="submit" className="btn-primary btn-block" disabled={busy || !email || !password}>
            {busy ? <Dots /> : isRegister ? "Create account" : "Log in"}
          </button>

          {waking && (
            <p className="auth-waking">
              Waking up the server… on the free plan the first request can take up to a minute.
            </p>
          )}

          <p className="auth-switch">
            {isRegister ? "Already have an account?" : "New here?"}{" "}
            <button type="button" onClick={() => switchMode(isRegister ? "login" : "register")}>
              {isRegister ? "Log in" : "Create an account"}
            </button>
          </p>
        </form>
      </section>
    </div>
  );
}
