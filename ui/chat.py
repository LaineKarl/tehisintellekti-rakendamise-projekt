"""Vestlusajaloo debug-paneelid ja tagasiside vormid."""

from datetime import datetime

import streamlit as st
import pandas as pd

from core.config import ERROR_STEP_OPTIONS, RAG_DISPLAY_COLS
from core.logger import log_feedback


def render_debug_info(debug: dict, message_index: int):
    """Kuvab vahesammude laienduspaneelid ühe vastuse kohta."""
    # Vahesamm 1
    with st.expander("🔍 Vahesamm 1 – Metaandmete filtreerimine"):
        st.caption(f"**Aktiivsed filtrid:** {debug.get('filters', '–')}")
        fc = debug.get("filtered_count", 0)
        st.write(f"Filtrid jätsid andmestikku alles **{fc}** kursust.")
        if fc == 0:
            st.warning("⚠️ Ükski kursus ei vastanud filtritele – kontekst on tühi!")

    # Vahesamm 2
    with st.expander("🔍 Vahesamm 2 – RAG vektorotsing (Top-N tulemused)"):
        ctx_df = debug.get("context_df", pd.DataFrame())
        if not ctx_df.empty:
            cols_to_show = [c for c in RAG_DISPLAY_COLS if c in ctx_df.columns]
            st.dataframe(ctx_df[cols_to_show], hide_index=True)
        else:
            st.warning("Ühtegi kursust ei leitud.")

    # Vahesamm 3
    with st.expander("🔍 Vahesamm 3 – LLM-ile saadetud süsteemiviip"):
        st.text_area(
            "Täpne prompt LLM-ile:",
            debug.get("system_prompt", ""),
            height=160,
            disabled=True,
            key=f"prompt_area_{message_index}",
        )


def render_feedback_form(message: dict, debug: dict, message_index: int):
    """Kuvab tagasiside vormi ühe vastuse kohta."""
    with st.expander("📝 Hinda vastust (salvestab logisse)"):
        with st.form(key=f"feedback_form_{message_index}"):
            rating = st.radio(
                "Hinnang vastusele:", ["👍 Hea", "👎 Halb"],
                horizontal=True, key=f"rating_{message_index}",
            )
            error_step = st.selectbox(
                "Kui vastus oli halb – mis samm põhjustas vea?",
                ERROR_STEP_OPTIONS,
                key=f"kato_{message_index}",
            )
            if st.form_submit_button("Salvesta hinnang"):
                _save_feedback(message, debug, rating, error_step)


def _save_feedback(message: dict, debug: dict, rating: str, error_step: str):
    """Salvestab tagasiside logifaili."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx_df = debug.get("context_df", pd.DataFrame())
    ctx_ids = ctx_df["unique_ID"].tolist() if not ctx_df.empty else []
    name_col = next(
        (c for c in ["nimi_et", "aine_nimetus_est"] if c in ctx_df.columns), None
    )
    ctx_names = ctx_df[name_col].tolist() if (name_col and not ctx_df.empty) else []

    log_feedback(
        ts,
        debug.get("user_prompt", ""),
        debug.get("filters", ""),
        debug.get("filtered_count", 0),
        ctx_ids, ctx_names,
        message["content"],
        rating, error_step,
    )
    st.success("✅ Tagasiside salvestatud faili tagasiside_log.csv!")
