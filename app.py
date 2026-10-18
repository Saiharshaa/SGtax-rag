"""Streamlit app: cited answers to Singapore corporate income tax questions.

    streamlit run app.py

Reads GROQ_API_KEY and GEMINI_API_KEY (one is enough to answer) and, if set, APP_PASSWORD from the
environment or .env. Until the Gemini index is complete, answers come from BM25 retrieval and say so.
"""

import hmac
import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from rag.display import RETRIEVAL_LABELS, excerpt, markdown_safe
from rag.embed import MissingApiKey
from rag.generate import Answer, answer_best_available
from rag.llm import LLMUnavailable, default_models
from rag.retrieve import Retriever

ROOT = Path(__file__).resolve().parent
EXAMPLES = [
    "Can a company deduct expenses it incurred before it started its business?",
    "How much renovation and refurbishment spending can be deducted, and over what period?",
    "Can a loss-making company transfer its losses to a sister company?",
]
# (tab label, retrieval config, fallback config when embeddings are unavailable)
IMPROVED = ("Structure-aware (this project)", "improved", "improved_bm25")
BASELINE = ("Naive baseline", "baseline", "naive_bm25")

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="SG Tax Answers", page_icon=":material/gavel:", layout="centered")


def password_ok() -> bool:
    expected = os.environ.get("APP_PASSWORD", "")
    if not expected or st.session_state.get("signed_in"):
        return True
    with st.form("sign_in"):
        entered = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            if hmac.compare_digest(entered.encode(), expected.encode()):
                st.session_state.signed_in = True
                st.rerun()
            st.error("That password isn't right.")
    return False


@st.cache_resource(show_spinner="Loading the index…")
def pipeline() -> tuple[Retriever, list]:
    retriever = Retriever(ROOT / "index")
    retriever.corpus("structured")   # load chunks and BM25 once, not on the first question
    return retriever, default_models()


def run(question: str, retriever: Retriever, models: list, compare: bool) -> list[dict]:
    runs = [IMPROVED, BASELINE] if compare else [IMPROVED]
    results = []
    for label, config, fallback in runs:
        started = time.monotonic()
        try:
            result, _ = answer_best_available(question, retriever, models, config, fallback)
            results.append({"label": label, "answer": result, "seconds": time.monotonic() - started})
        except LLMUnavailable:
            results.append({"label": label, "error": "Groq and Gemini both failed to answer. Try again in a minute."})
    return results


def show_answer(result: Answer, seconds: float) -> None:
    if result.refused:
        st.info(result.text)
    else:
        st.markdown(markdown_safe(result.text))
    model = result.model.split(":", 1)[-1] if result.model else "no model called"
    st.caption(f"{model} · {seconds:.1f} s · {RETRIEVAL_LABELS.get(result.config, result.config)}")
    if result.cited:
        with st.expander(f"Sources cited ({len(result.cited)})"):
            for chunk in result.cited:
                heading = f" · {chunk.heading}" if chunk.heading else ""
                st.markdown(f"**{markdown_safe(chunk.cite or chunk.doc_title)}**{markdown_safe(heading)}")
                st.caption(markdown_safe(excerpt(chunk.text)))


def show_results(results: list[dict]) -> None:
    containers = st.tabs([r["label"] for r in results]) if len(results) > 1 else [st.container()]
    for container, result in zip(containers, results):
        with container:
            if "error" in result:
                st.error(result["error"])
            else:
                show_answer(result["answer"], result["seconds"])


st.title("Singapore corporate income tax, cited")
st.caption("Answers come only from the Income Tax Act 1947 (2020 Revised Edition, version in force from "
           "11 Sep 2026) and five IRAS e-Tax guides (published 30 Jan 2026), with a section or paragraph cited "
           "for every statement. A study tool for tax associates, not tax advice: check the cited provision "
           "before relying on an answer.")

if not password_ok():
    st.stop()
try:
    retriever, models = pipeline()
except (MissingApiKey, FileNotFoundError) as error:
    st.error(f"The app isn't set up yet: {error}")
    st.stop()

compare = st.toggle("Compare with the naive baseline",
                    help="The same model given 500-token chunks without section structure: the approach this "
                         "project measures itself against.")
history = st.session_state.setdefault("history", [])

question = st.chat_input("Ask a Singapore corporate income tax question")
if not history and not question:
    st.markdown("**Try one of these:**")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            question = example

for turn in history:
    with st.chat_message("user"):
        st.markdown(markdown_safe(turn["question"]))
    with st.chat_message("assistant"):
        show_results(turn["results"])

if question:
    with st.chat_message("user"):
        st.markdown(markdown_safe(question))
    with st.chat_message("assistant"):
        with st.spinner("Searching the Act and the e-Tax guides…"):
            results = run(question, retriever, models, compare)
        show_results(results)
    history.append({"question": question, "results": results})
    st.rerun()   # redraw from history, so the example buttons go once a question is asked
