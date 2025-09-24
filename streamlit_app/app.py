import queue
import subprocess
import threading
import time
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
CSS_DIR = BASE_DIR / "styles"

# --- Page config ---
st.set_page_config(
    page_title="Járókelő RAG",
    page_icon="🟢",
    layout="centered"
)

# --- Title & intro ---
st.title("Járókelő RAG Explorer")
st.markdown(
    """
    <p style="font-style: italic; font-size: 16px;">
        If you’re not familiar with <b>Járókelő</b>, it’s a Hungarian civic platform where citizens can report and track local public issues (like broken streetlights or potholes).
        The organization forwards these reports to the relevant authorities, monitors the resolution status, and sends reminders to ensure the requested changes are addressed.
        Learn more at <a href="https://jarokelo.hu" style="color:#4A90E2;">jarokelo.hu</a>.
    </p>
    """,
    unsafe_allow_html=True
)
st.markdown(
    "Ask questions about the data collected from Járókelő and get answers based on the relevant information retrieved from the dataset."
)

# --- State ---
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

if "debug_lines" not in st.session_state:
    st.session_state.debug_lines = [] 

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

def load_css(filename: str):
    css_path = CSS_DIR / filename
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Apply theme CSS
if st.session_state.dark_mode:
    load_css(Path(__file__).resolve().parent / "styles" / "dark.css")
else:
    load_css(Path(__file__).resolve().parent / "styles" / "light.css")

# --- Input form ---
with st.form("query_form", clear_on_submit=False):
    query = st.text_input(
        "What do you want to ask from my Járókelő RAG?",
        placeholder="Type your question and press Enter..."
    )

    col_btn, col_counter = st.columns([1, 1])
    submitted = col_btn.form_submit_button("Ask")
    counter_placeholder = col_counter.empty()

    col_check, _ = st.columns([1, 1])
    col_check.checkbox(
        "Debug mode (show all RAG logs)",
        key="debug_mode"
    )

    debug_log_box = st.empty()
    if st.session_state.debug_mode:
        debug_content = "".join(st.session_state.debug_lines)
        debug_log_box.text_area("Debug log", value=debug_content, height=200, key="debug_area_live")

def run_rag_pipeline(cmd, debug_log_box, counter_placeholder):
    st.session_state.debug_lines = []
    start_time = time.time()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    q = queue.Queue()

    def enqueue_output(out, q):
        for line in iter(out.readline, ''):
            q.put(line)
        out.close()

    t = threading.Thread(target=enqueue_output, args=(process.stdout, q))
    t.daemon = True
    t.start()

    while True:
        if process.poll() is not None and q.empty():
            break

        while not q.empty():
            line = q.get()
            if st.session_state.debug_mode:
                st.session_state.debug_lines.append(line)
                debug_content = "".join(st.session_state.debug_lines)
                debug_log_box.text_area("Debug log", value=debug_content, height=200)

        elapsed = int(time.time() - start_time)
        minutes, seconds = divmod(elapsed, 60)
        counter_placeholder.markdown(
            f"Running... {minutes} min {seconds} sec" if minutes else f"Running... {seconds} sec"
        )
        time.sleep(0.1)

    t.join()
    # stdout, stderr = process.communicate()
    debug_content = "".join(st.session_state.debug_lines)
    # debug_log_box.text_area("Debug log", value=debug_content, height=200)
    debug_log_box.text_area("Debug log", value=debug_content, height=200, key="debug_area_final")

    marker = "FINAL RAG OUTPUT:"
    debug_text = "".join(st.session_state.debug_lines)
    if marker in debug_text:
        answer = debug_text.rsplit(marker, 1)[-1].strip()
    else:
        answer = "No RAG output found."
    st.session_state.last_answer = answer

    total_time = int(time.time() - start_time)
    return answer, total_time

# --- Handle form submission ---
if submitted and query:
    answer_placeholder = st.empty()
    counter_placeholder.markdown("Running... 0 sec")
    # Use the single debug_log_box
    cmd = [
        "poetry", "run", "python", "./src/jarokelo_tracker/rag_pipeline.py",
        "--query", query,
        "--vector-backend", "faiss",
        "--embedding-provider", "local",
        "--local-model", "distiluse-base-multilingual-cased-v2",
        "--headless", "true",
        "--top_k", "20"
    ]

    with st.spinner("🔎 Processing your request, please wait..."):
        answer, total_time = run_rag_pipeline(cmd, debug_log_box, counter_placeholder)
        answer_placeholder.markdown(
            f"<div class='result-box'>{answer}<br><small>Completed in {total_time} sec</small></div>",
            unsafe_allow_html=True
        )
