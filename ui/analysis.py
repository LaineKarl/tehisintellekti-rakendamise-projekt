"""Vigade analüüsi kuva logifaili põhjal."""

import os

import streamlit as st
import pandas as pd

from core.config import LOG_FILE


def render_error_analysis():
    """Kuvab vigade analüüsi sektsiooni logifaili põhjal."""
    st.subheader("📊 Vigade analüüs logist")

    if not os.path.isfile(LOG_FILE):
        st.info("Logifaili pole veel loodud. Tee mõned päringud ja anna tagasisidet.")
        return

    log_df = pd.read_csv(LOG_FILE)
    bad = log_df[log_df["Hinnang"] == "👎 Halb"]
    st.write(f"**Kokku päringuid:** {len(log_df)} | **Halbu vastuseid:** {len(bad)}")

    if len(bad) == 0:
        st.success("Logis ei ole ühtegi halba vastust – suurepärane!")
        return

    step_counts = bad["Viga sammus"].value_counts().reset_index()
    step_counts.columns = ["Vahesamm", "Vigade arv"]
    step_counts["% kõikidest vigadest"] = (
        step_counts["Vigade arv"] / len(bad) * 100
    ).round(1)

    st.write("**Vigade jaotus vahesammude kaupa:**")
    st.dataframe(step_counts, hide_index=True)
    st.bar_chart(step_counts.set_index("Vahesamm")["Vigade arv"])

    st.write("**Halvad juhtumid detailidega:**")
    detail_cols = [
        "Aeg", "Kasutaja päring", "Filtrid", "Filtreeritud kursusi", "Viga sammus",
    ]
    cols_show = [c for c in detail_cols if c in bad.columns]
    st.dataframe(bad[cols_show], hide_index=True)
