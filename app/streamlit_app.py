"""Streamlit UI: index a repo up top, chat below with cited answers."""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from config import CONFIG
from src.pipeline.rag import RAGPipeline
from src.storage.index_meta import read_index_meta

# Streamlit has no login, so it uses one shared index namespace.
USER_ID = "streamlit"

st.set_page_config(page_title="Chat with a Codebase", page_icon="💬", layout="wide")

SKYMINT = "#B8F7E4"
GRAPHITE = "#25272C"
_LANG_HINT = {"js": "javascript", "ts": "typescript", "csharp": "csharp", "cpp": "cpp"}

CSS = """
<style>
:root { --skymint:#B8F7E4; --graphite:#25272C; --card:#2E3138; --muted:#9AA0A6; }

.stApp { background: radial-gradient(1200px 600px at 50% -10%, #30343B 0%, #25272C 55%); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; max-width: 1000px; }

/* ---- Hero ---- */
.hero-title { font-size: 2.4rem; font-weight: 800; color: #F5F7F8; letter-spacing: -.5px; margin: 0; }
.hero-title .accent { color: var(--skymint); }
.hero-sub { color: var(--muted); font-size: .98rem; margin-top: .35rem; }

/* ---- Section label ---- */
.section-label { color: var(--skymint); font-size: .78rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; margin: 1.6rem 0 .5rem; }

/* ---- Index chip ---- */
.chip { display:inline-flex; align-items:center; gap:.5rem; padding:.4rem .9rem; border-radius:999px;
  font-size:.85rem; font-weight:600; background:rgba(184,247,228,.12); color:var(--skymint);
  border:1px solid rgba(184,247,228,.32); }
.chip.idle { background:rgba(154,160,166,.1); color:var(--muted); border-color:rgba(154,160,166,.28); }
.chip .dot { width:8px; height:8px; border-radius:50%; background:var(--skymint); box-shadow:0 0 8px var(--skymint); }
.chip-meta { color:var(--muted); font-size:.82rem; margin-left:.2rem; }

/* ---- Inputs ---- */
.stTextInput input, [data-testid="stChatInput"] textarea {
  background:#22242A !important; color:#E8EAED !important; border:1px solid rgba(255,255,255,.1) !important;
  border-radius:12px !important; }
.stTextInput input:focus, [data-testid="stChatInput"] textarea:focus {
  border-color:var(--skymint) !important; box-shadow:0 0 0 2px rgba(184,247,228,.25) !important; }
[data-testid="stChatInput"] { border-radius:14px; }

/* ---- Buttons ---- */
.stButton>button, .stFormSubmitButton>button {
  background:var(--skymint); color:var(--graphite); font-weight:700; border:none; border-radius:12px;
  padding:.55rem 1.3rem; transition:all .18s ease; width:100%; }
.stButton>button:hover, .stFormSubmitButton>button:hover {
  color:var(--graphite); box-shadow:0 0 0 3px rgba(184,247,228,.32); transform:translateY(-1px); }

/* ---- Chat bubbles ---- */
.user-row { display:flex; justify-content:flex-end; margin:.6rem 0; }
.user-bubble { background:linear-gradient(135deg,#B8F7E4,#8FE9D0); color:#1A2A26; font-weight:500;
  padding:.7rem 1rem; border-radius:16px 16px 4px 16px; max-width:78%; box-shadow:0 4px 14px rgba(0,0,0,.25); }
[data-testid="stChatMessage"] { background:var(--card); border:1px solid rgba(184,247,228,.14);
  border-radius:16px 16px 16px 4px; padding:.4rem .3rem; box-shadow:0 4px 14px rgba(0,0,0,.2); }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] { background:#1F2126; border-right:1px solid rgba(184,247,228,.1); }
[data-testid="stSidebar"] .section-label { margin-top:.6rem; }

/* ---- Sources expander ---- */
[data-testid="stExpander"] { border:1px solid rgba(255,255,255,.08); border-radius:12px; background:#22242A; }

/* ---- Animated loaders ---- */
@keyframes spin { to { transform:rotate(360deg); } }
@keyframes bounce { 0%,80%,100%{ transform:scale(.3); opacity:.4;} 40%{ transform:scale(1); opacity:1;} }
.loader { display:flex; flex-direction:column; align-items:center; gap:1.1rem; padding:2.2rem 1rem; }
.ring { width:58px; height:58px; border-radius:50%;
  background:conic-gradient(from 0deg, var(--skymint), rgba(184,247,228,.05) 65%);
  -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 6px), #000 0);
          mask:radial-gradient(farthest-side, transparent calc(100% - 6px), #000 0);
  animation:spin 1s linear infinite; }
.loader-text { color:var(--skymint); font-weight:600; font-size:.95rem; }
.loader-sub { color:var(--muted); font-size:.8rem; margin-top:-.6rem; }
.dots span { display:inline-block; width:9px; height:9px; margin:0 3px; border-radius:50%;
  background:var(--skymint); animation:bounce 1.3s infinite ease-in-out both; }
.dots span:nth-child(1){ animation-delay:-.32s; } .dots span:nth-child(2){ animation-delay:-.16s; }
.thinking { display:flex; align-items:center; gap:.6rem; color:var(--muted); font-size:.9rem; padding:.3rem; }
</style>
"""

RING_LOADER = """
<div class="loader">
  <div class="ring"></div>
  <div class="loader-text">{title}</div>
  <div class="loader-sub">{sub}</div>
</div>
"""

THINKING = """
<div class="thinking"><span class="dots"><span></span><span></span><span></span></span> {label}</div>
"""


@st.cache_resource(show_spinner=False)
def get_pipeline() -> RAGPipeline:
    return RAGPipeline(USER_ID)


def render_header() -> None:
    st.markdown(
        '<div class="hero-title">💬 Chat with a <span class="accent">Codebase</span></div>'
        '<div class="hero-sub">Point it at any GitHub repo and ask questions — grounded '
        "answers with real <code>file:line</code> citations.</div>",
        unsafe_allow_html=True,
    )


def render_index_bar() -> None:
    st.markdown('<div class="section-label">Repository</div>', unsafe_allow_html=True)
    meta = read_index_meta(USER_ID)
    if meta:
        st.markdown(
            f'<span class="chip"><span class="dot"></span>{meta["source"]}</span>'
            f'<span class="chip-meta">  ·  {meta["n_files"]} files · {meta["n_chunks"]} chunks · '
            f'{meta["embed_model"].split("/")[-1]}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<span class="chip idle">No repository indexed yet</span>', unsafe_allow_html=True)

    with st.form("ingest", clear_on_submit=False):
        c1, c2 = st.columns([5, 1])
        src = c1.text_input(
            "repo", label_visibility="collapsed",
            placeholder="Paste a GitHub URL, e.g. https://github.com/pallets/click.git",
        )
        go = c2.form_submit_button("Ingest")

    loader = st.empty()
    if go and src:
        loader.markdown(
            RING_LOADER.format(title="Indexing repository…",
                               sub="cloning → chunking → embedding"),
            unsafe_allow_html=True,
        )
        try:
            n = get_pipeline().ingest(src)
            get_pipeline.clear()
            st.session_state.messages = []
            loader.empty()
            st.success(f"Indexed {n} chunks — ask away below.")
            st.rerun()
        except Exception as e:
            loader.empty()
            st.error(f"Ingest failed: {type(e).__name__}: {e}")


def render_sources(sources) -> None:
    with st.expander(f"📄 Sources ({len(sources)})"):
        for hit in sources:
            c = hit.chunk
            st.markdown(f"**`{c.citation()}`** · score {hit.score:.2f}")
            st.code(c.text, language=_LANG_HINT.get(c.language, c.language))


def render_user(text: str) -> None:
    safe = html.escape(text).replace("\n", "<br>")
    st.markdown(f'<div class="user-row"><div class="user-bubble">{safe}</div></div>',
                unsafe_allow_html=True)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="section-label">Settings</div>', unsafe_allow_html=True)
        st.toggle("🤖 Agentic mode", key="agentic",
                  help="Self-correcting: grades retrieved code and rewrites the query to retry if it's weak.")
        if st.button("🗑 Clear chat"):
            st.session_state.messages = []
            st.rerun()
        st.markdown('<div class="section-label">Engine</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:#9AA0A6;font-size:.85rem;line-height:1.7">'
            f'LLM &nbsp;<code>{CONFIG.llm_provider}</code><br>'
            f'Model &nbsp;<code>{CONFIG.llm_model.split("/")[-1]}</code><br>'
            f'Retriever &nbsp;<code>{CONFIG.retriever}{" + rerank" if CONFIG.rerank else ""}</code>'
            "</div>",
            unsafe_allow_html=True,
        )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    render_sidebar()
    render_header()
    render_index_bar()

    if read_index_meta(USER_ID) is None:
        st.info("Index a repository above to start chatting.")
        return

    st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)
    st.session_state.setdefault("messages", [])

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            render_user(msg["content"])
        else:
            with st.chat_message("assistant", avatar="💠"):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    render_sources(msg["sources"])

    question = st.chat_input("Ask about the codebase…")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    render_user(question)

    agentic = st.session_state.get("agentic", False)
    with st.chat_message("assistant", avatar="💠"):
        ph = st.empty()
        label = "Agent: retrieve → grade → rewrite → answer…" if agentic else "Retrieving + answering…"
        ph.markdown(THINKING.format(label=label), unsafe_allow_html=True)
        try:
            pipe = get_pipeline()
            answer = pipe.answer_agentic(question) if agentic else pipe.answer(question)
            ph.empty()
            if answer.trace and answer.trace.get("rewrites"):
                st.caption(f"🔁 agent rewrote the query {answer.trace['rewrites']}×")
            st.markdown(answer.text)
            render_sources(answer.sources)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer.text, "sources": answer.sources}
            )
        except Exception as e:
            ph.empty()
            err = f"LLM/retrieval error: {type(e).__name__}: {e}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})


main()
