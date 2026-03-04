"""AI Kursuse Nõustaja – Streamlit rakenduse sisenemispunkt."""

import streamlit as st

from core import DEFAULT_SESSION_STATE
from core import load_data, update_cost
from pipeline import build_filter_description, apply_metadata_filters
from pipeline import perform_rag_search
from pipeline import build_system_prompt, stream_llm_response
from ui import (
    render_sidebar, render_debug_info, render_feedback_form,
    render_error_analysis, run_tests,
)

# ─── KONFIGURATSIOON ──────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Kursuse Nõustaja", page_icon="🎓", layout="wide")

# ─── SESSIOONIOLEKU INITSIALISEERIMINE ────────────────────────────────────────
for key, val in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = val if not isinstance(val, list) else []

# ─── ANDMETE LAADIMINE ───────────────────────────────────────────────────────
embedder, merged_df = load_data()

# ─── PEALEHT ─────────────────────────────────────────────────────────────────
st.title("🎓 AI ÕIS2 Kursuste Nõustaja")
st.caption(
    "RAG süsteem koos vahesammude logimise, kapotialuse analüüsi, "
    "tagasiside ja vigade analüüsiga."
)

settings = render_sidebar(merged_df)

# ─── VIGADE ANALÜÜS ──────────────────────────────────────────────────────────
if st.session_state.get("show_analysis", False):
    render_error_analysis()
    if st.button("Sulge analüüs"):
        st.session_state.show_analysis = False
        st.rerun()

# ─── AUTOMAATTESTIMINE ───────────────────────────────────────────────────────
if st.session_state.get("show_testing", False):
    run_tests(
        embedder=embedder,
        merged_df=merged_df,
        model=settings["model"],
        n_tests=st.session_state.get("n_tests", 10),
        results_n=settings["results_n"],
    )
    if st.button("Sulge testid"):
        st.session_state.show_testing = False
        st.rerun()

st.divider()

# ─── VESTLUSAJALUGU ──────────────────────────────────────────────────────────
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "debug_info" in message:
            render_debug_info(message["debug_info"], i)
            render_feedback_form(message, message["debug_info"], i)

# ─── PEAMINE SISEND ──────────────────────────────────────────────────────────
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):
    filter_desc = build_filter_description(settings["filters"])

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not settings["api_key"]:
            err = "⚠️ Palun sisesta API võti külgribal!"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
        else:
            with st.spinner("Otsin sobivaid kursusi..."):
                # Samm 1: Metaandmete filtreerimine
                filtered_df = apply_metadata_filters(merged_df, settings["filters"])

                # Samm 2: RAG vektorotsing
                context_text, results_df_display = perform_rag_search(
                    embedder, prompt, filtered_df, settings["results_n"]
                )
                if filtered_df.empty:
                    st.warning(context_text)

                # Samm 3: LLM vastuse genereerimine
                system_prompt = build_system_prompt(filter_desc, context_text)

                try:
                    response_text, in_tok, out_tok = stream_llm_response(
                        settings["model"], system_prompt
                    )
                    update_cost(in_tok, out_tok, settings["model"])

                    st.caption(
                        f"🔢 See päring: {in_tok:,} sisend + {out_tok:,} väljund tokenit | "
                        f"Kokku kulu: ${st.session_state.total_cost_usd:.6f}"
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "debug_info": {
                            "user_prompt":    prompt,
                            "filters":        filter_desc,
                            "filtered_count": len(filtered_df),
                            "context_df":     results_df_display,
                            "system_prompt":  system_prompt,
                        },
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Viga API päringul: {e}")
