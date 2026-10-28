import csv
import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from ingest import ingest
from rag_chain import answer_question
from retriever import get_db, reset_db
from scrape import scrape_all

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
UNANSWERED_CSV = DATA_DIR / "unanswered_questions.csv"
LEADS_CSV = DATA_DIR / "leads.csv"

SAMPLE_QUESTIONS = [
    "How much does anal cancer treatment cost in Tijuana?",
    "What is included in the out-patient program?",
    "Is ozone therapy cheaper in Turkey or Mexico?",
    "ٹیجوانا میں کینسر کے علاج کی قیمت کیا ہے؟",
]

QUOTE_INTENT = re.compile(
    r"\b(quote|book|booking|appointment|contact|consultation|schedule)\b", re.I
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Each paragraph picks its own direction, so Urdu and Arabic read right to left.
CSS = """
<style>
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    unicode-bidi: plaintext;
    text-align: start;
}
</style>
"""


# ---------- helpers ----------

def safe(text):
    """Streamlit treats $...$ as math. Escape it so prices show correctly."""
    return text.replace("$", "\\$")


def append_csv(path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(header)
        writer.writerow(row)


def log_if_unanswered(question, result):
    """Save questions the bot could not answer from the content."""
    if result.get("error"):
        reason = "error"
    elif not result["found"]:
        reason = "no_content_found"
    elif not result["sources"]:
        reason = "no_source_used"
    else:
        return
    append_csv(
        UNANSWERED_CSV,
        ["time", "question", "search_query", "reason"],
        [datetime.now().isoformat(timespec="seconds"), question,
         result["search_query"], reason],
    )


def show_sources(sources):
    if sources:
        st.markdown("**Sources:**")
        for s in sources:
            st.markdown(f"- [{s['title']}]({s['url']})")


# ---------- index ----------

def index_ready():
    try:
        return get_db()._collection.count() > 0
    except Exception:
        return False


def build_index():
    """Scrape only if there is no saved data, then build the index."""
    if not list(RAW_DIR.glob("*.json")):
        scrape_all()
    ingest()
    reset_db()


@st.cache_resource(show_spinner=False)
def ensure_index():
    if not index_ready():
        build_index()
    return True


# ---------- lead form ----------

def lead_form(last_question):
    with st.form("lead_form", clear_on_submit=True):
        st.markdown("**Want a free quote?** Leave your details and we will save your request.")
        name = st.text_input("Name")
        email = st.text_input("Email")
        agree = st.checkbox("I agree to be contacted about my quote request")
        sent = st.form_submit_button("Send")
    if sent:
        if not name.strip():
            st.error("Please enter your name.")
        elif not EMAIL_PATTERN.match(email.strip()):
            st.error("Please enter a valid email.")
        elif not agree:
            st.error("Please tick the box to continue.")
        else:
            append_csv(
                LEADS_CSV,
                ["time", "name", "email", "last_question"],
                [datetime.now().isoformat(timespec="seconds"),
                 name.strip(), email.strip(), last_question],
            )
            st.session_state.show_lead = False
            st.success("Thank you! Your request was saved.")


# ---------- page ----------

st.set_page_config(page_title="PlacidWay Assistant", page_icon="💬")
st.markdown(CSS, unsafe_allow_html=True)
st.title("PlacidWay Assistant")
st.caption("Answers come only from a small set of PlacidWay pages.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_lead" not in st.session_state:
    st.session_state.show_lead = False

# sidebar
with st.sidebar:
    st.header("About")
    st.info(
        "This assistant shares information from PlacidWay pages. "
        "It is not medical advice. Please talk to your doctor "
        "before making any treatment decision."
    )
    if st.button("Refresh content", use_container_width=True):
        with st.spinner("Reading the pages again and rebuilding the index..."):
            try:
                saved = scrape_all()
                if saved == 0:
                    st.error("No pages could be downloaded. The old content is kept.")
                else:
                    ingest()
                    reset_db()
                    st.success(f"Content updated ({saved} pages).")
            except Exception as e:
                st.error(f"Refresh failed: {e}")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.show_lead = False

# make sure the index exists (first start on a new server)
try:
    with st.spinner("Preparing the knowledge base. The first start can take a few minutes..."):
        ensure_index()
except Exception as e:
    st.error(f"Could not prepare the knowledge base: {e}")
    st.stop()

# chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(safe(m["content"]))
        show_sources(m.get("sources", []))

# sample question buttons (only on an empty chat)
clicked = None
if not st.session_state.messages:
    st.markdown("**Try a question:**")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            clicked = q

question = st.chat_input("Ask about treatments, clinics or costs") or clicked

if question:
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(safe(question))

    with st.chat_message("assistant"):
        with st.spinner("Searching the PlacidWay pages..."):
            result = answer_question(question, history)
        st.markdown(safe(result["answer"]))
        show_sources(result["sources"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
    log_if_unanswered(question, result)
    st.session_state.show_lead = bool(QUOTE_INTENT.search(question))

if st.session_state.show_lead:
    last = st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else ""
    lead_form(last)