import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err.message || "An error occurred");
    }
  };

  return (
    <div className="login-container" style={{ maxWidth: "400px", margin: "100px auto", padding: "20px", background: "var(--bg-panel)", borderRadius: "8px", boxShadow: "0 4px 6px rgba(0,0,0,0.1)" }}>
      <h2 style={{ textAlign: "center", marginBottom: "20px" }}>{isRegister ? "Create an Account" : "Welcome Back"}</h2>
      {error && <div style={{ color: "var(--red)", marginBottom: "15px", textAlign: "center" }}>{error}</div>}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
        <input 
          type="email" 
          placeholder="Email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required 
          style={{ padding: "10px", borderRadius: "4px", border: "1px solid var(--border)" }}
        />
        <input 
          type="password" 
          placeholder="Password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
          style={{ padding: "10px", borderRadius: "4px", border: "1px solid var(--border)" }}
        />
        <button type="submit" style={{ padding: "10px", background: "var(--accent)", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}>
          {isRegister ? "Register" : "Login"}
        </button>
      </form>
      <p style={{ textAlign: "center", marginTop: "15px", fontSize: "0.9rem" }}>
        {isRegister ? "Already have an account?" : "Don't have an account?"} {" "}
        <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(!isRegister); }} style={{ color: "var(--accent)", textDecoration: "none" }}>
          {isRegister ? "Login here" : "Register here"}
        </a>
      </p>
    </div>
  );
}
