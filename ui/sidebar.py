"""Külgriba – seaded, filtrid, kulu jälgimine."""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from core.config import MODEL_PRICES, DEFAULT_SESSION_STATE, LINN_MAP
from core.data import get_unique_sorted


load_dotenv()  # Laeb .env-faili keskkonnamuutujad

def render_sidebar(merged_df: pd.DataFrame) -> dict:
    """Kuvab külgriba ja tagastab kasutaja seaded dict'ina."""
    with st.sidebar:
        st.header("⚙️ Seaded")
        api_key = os.getenv("API_KEY", "")
        selected_model = st.selectbox("Mudel", list(MODEL_PRICES.keys()))

        if not api_key:
            st.warning("⚠️ API_KEY puudub .env failist!")

        st.divider()
        st.subheader("🔍 Metaandmete filtrid")
        st.caption("Jäta tühjaks, kui filter pole oluline.")

        semesters = ["(kõik)"] + get_unique_sorted(merged_df, "semester")
        sel_semester = st.selectbox("Semester", semesters)

        eap_values = ["(kõik)"] + [str(v) for v in get_unique_sorted(merged_df, "eap")]
        sel_eap = st.selectbox("EAP maht", eap_values)

        if "language" in merged_df.columns:
            langs = ["(kõik)"] + get_unique_sorted(merged_df, "language")
            sel_lang = st.selectbox("Keel", langs)
        else:
            sel_lang = "(kõik)"

        hindamis_opts = st.multiselect("Hindamisviis", ["Eristav", "Eristamata"])
        linn_opts     = st.multiselect("Linn", list(LINN_MAP.keys()))
        aste_opts     = st.multiselect("Õppeaste", ["bakalaureuse", "magistri", "doktori"])
        veeb_opts     = st.multiselect("Õppevorm", ["põimõpe", "lähiõpe", "veebiõpe"])
        no_prereqs    = st.checkbox("Ainult ilma eeldusaineteta kursused")
        results_n     = st.slider("Kuvatavate kursuste arv (Top-N)", 1, 20, 5)

        st.divider()
        st.subheader("💰 Kulu jälgimine")
        col_a, col_b = st.columns(2)
        col_a.metric("Sisend-tokenid", f"{st.session_state.total_input_tokens:,}")
        col_b.metric("Väljund-tokenid", f"{st.session_state.total_output_tokens:,}")
        st.metric("Jooksev kulu (USD)", f"${st.session_state.total_cost_usd:.6f}")

        if st.button("🔄 Nulli vestlus ja kulu"):
            for key, val in DEFAULT_SESSION_STATE.items():
                st.session_state[key] = val if not isinstance(val, list) else []
            st.rerun()

        st.divider()
        st.subheader("📊 Vigade analüüs")
        if st.button("Näita vigade analüüsi"):
            st.session_state.show_analysis = True

        st.divider()
        st.subheader("🧪 Testimine")
        total_tests = 75  # testjuhtumid.csv ridade arv
        n_tests = st.slider("Testide arv", 1, total_tests, 10)
        if st.button("▶️ Jooksuta testid"):
            st.session_state.show_testing = True
            st.session_state.n_tests = n_tests

    return {
        "api_key": api_key,
        "model": selected_model,
        "results_n": results_n,
        "filters": {
            "semester": sel_semester,
            "eap": sel_eap,
            "lang": sel_lang,
            "hindamisviis": hindamis_opts,
            "linn": linn_opts,
            "aste": aste_opts,
            "veeb": veeb_opts,
            "no_prereqs": no_prereqs,
        },
    }
