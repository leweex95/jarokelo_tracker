import streamlit as st
import subprocess
import json
import time
from pathlib import Path

# --- Page config ---
st.set_page_config(
    page_title="Járókelő RAG",
    page_icon="🟢",
    layout="centered"
)

# --- Gradient background ---
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(135deg, #4A90E2, #50E3C2);
        color: white;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    .result-box {
        background-color: rgba(255,255,255,0.15);
        padding: 1rem;
        border-radius: 10px;
        margin-top: 1rem;
        color: white;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Title ---
st.title("🟢 Járókelő RAG Explorer")

# --- State ---
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

# --- Theme toggle state ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # initialize first

# --- Theme toggle button ---
toggle = st.button("🌗 Switch Theme")
if toggle:
    st.session_state.dark_mode = not st.session_state.dark_mode

# --- Apply CSS based on theme ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default to dark

if st.session_state.dark_mode:
    st.markdown("""
    <style>
    /* top-level containers */
    .stApp, .stAppViewContainer, .stMain, .stMainBlockContainer, .stVerticalBlock {
        background-color: #0E1117 !important;
        color: #F5F5F5 !important;  /* silver text */
    }
    /* header */
    .stAppHeader, .stAppToolbar, .stToolbarActions, .stMainMenu, .stAppDeployButton {
        background-color: #0E1117 !important;
        color: #F5F5F5 !important;
    }
    /* Inputs */
    .stTextInput>div>div>input, .stTextInput>div>div>label, .stTextInput>div>div>p {
        background: #262730;
        color: #F5F5F5 !important;
        border-radius: 8px;
    }
    /* Buttons */
    button { 
        background-color: #262730 !important; 
        color: #E0E0E0 !important;
    }
    /* Result box */
    .result-box { 
        background-color: rgba(255,255,255,0.15); 
        color: #E0E0E0 !important;
        padding: 1rem; 
        border-radius: 10px; 
        margin-top: 1rem; 
    }
    </style>
    """, unsafe_allow_html=True)


else:
    st.markdown(
        """
        <style>
        body, .css-18e3th9, .css-1outpf7, .css-1v3fvcr {
            background-color: #FAFAFA !important;
            color: #0E1117 !important;
        }
        .stTextInput>div>div>input { background: #FFFFFF; color: #0E1117; border-radius: 8px; }
        .result-box { background-color: rgba(0,0,0,0.05); color: #0E1117; padding: 1rem; border-radius: 10px; margin-top: 1rem; }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Input ---
with st.form("query_form", clear_on_submit=False):
    query = st.text_input(
        "💡 What do you want to ask from my Járókelő RAG?",
        placeholder="Type your question and press Enter..."
    )
    submitted = st.form_submit_button("Ask")

# --- When query submitted ---
if submitted and query:
    with st.spinner("🔎 Processing your request, please wait..."):
        try:
            cmd = [
                "poetry", "run", "python", "./src/jarokelo_tracker/rag_pipeline.py",
                "--query", query,
                "--vector-backend", "faiss",
                "--embedding-provider", "local",
                "--local-model", "distiluse-base-multilingual-cased-v2",
                "--headless", "true",
                "--top_k", "20"
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            answer = result.stdout.strip()
            st.session_state.last_answer = answer or "⚠️ No response received."
        except subprocess.CalledProcessError as e:
            st.session_state.last_answer = f"❌ Error running pipeline:\n{e.stderr}"

# --- Output ---
if st.session_state.last_answer:
    st.markdown(f"<div class='result-box'>{st.session_state.last_answer}</div>", unsafe_allow_html=True)
