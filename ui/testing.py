"""Automaattestid – testjuhtumid.csv põhjal LLM täpsuse hindamine."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from pipeline.rag import perform_rag_search
from pipeline.llm import build_system_prompt

load_dotenv()

TEST_CSV = Path(__file__).resolve().parent.parent / "data" / "testjuhtumid.csv"


def _load_test_cases(n: int) -> pd.DataFrame:
    df = pd.read_csv(TEST_CSV)
    return df.head(n)


def run_tests(embedder, merged_df: pd.DataFrame, model: str, n_tests: int, results_n: int):
    """
    Jooksutab n_tests testjuhtumit CSV-st ja kuvab tulemused.

    Iga testjuhtum:
      - 1. veerg: kasutaja päring
      - 2. veerg: oodatavad kursuse ID-d (komaga eraldatud)
    """
    test_df = _load_test_cases(n_tests)
    col_query = test_df.columns[0]
    col_ids   = test_df.columns[1]

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("API_KEY"),
    )

    results = []
    progress_bar = st.progress(0, text="Testid käivad...")

    for i, (_, row) in enumerate(test_df.iterrows()):
        query        = str(row[col_query])
        expected_raw = str(row[col_ids])
        expected_ids = [eid.strip() for eid in expected_raw.split(",")]

        # Samm 1: RAG otsing (ilma metaandmete filtriteta)
        context_text, _ = perform_rag_search(embedder, query, merged_df.copy(), results_n)

        # Samm 2: LLM päring (ilma streaming'uta – kiirema testimise jaoks)
        system_prompt = build_system_prompt("pole (kõik kursused)", context_text)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": query},
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
            )
            answer = response.choices[0].message.content

            found   = [eid for eid in expected_ids if eid in answer]
            missing = [eid for eid in expected_ids if eid not in answer]
            passed  = len(missing) == 0

            results.append({
                "Päring":         query,
                "Oodatavad ID-d": expected_raw,
                "Leitud":         ", ".join(found)   if found   else "–",
                "Puudu":          ", ".join(missing) if missing else "–",
                "Tulemus":        "✅ Läbitud" if passed else "❌ Ebaõnnestus",
            })
        except Exception as e:
            results.append({
                "Päring":         query,
                "Oodatavad ID-d": expected_raw,
                "Leitud":         "–",
                "Puudu":          expected_raw,
                "Tulemus":        f"⚠️ Viga: {e}",
            })

        progress_bar.progress((i + 1) / n_tests, text=f"Test {i + 1}/{n_tests}...")

    progress_bar.empty()

    # ─── TULEMUSED ────────────────────────────────────────────────────────────
    results_df = pd.DataFrame(results)
    n_passed   = (results_df["Tulemus"] == "✅ Läbitud").sum()
    n_failed   = n_tests - n_passed
    pct        = round(n_passed / n_tests * 100, 1)

    st.subheader("🧪 Testi tulemused")

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Läbitud",     n_passed)
    col2.metric("❌ Ebaõnnestus", n_failed)
    col3.metric("Täpsus",         f"{pct}%")

    # Järeldus
    if pct >= 80:
        st.success(
            f"🎉 Suurepärane tulemus! Süsteem leidis oodatavad kursused "
            f"**{pct}%** juhtudest ({n_passed}/{n_tests})."
        )
    elif pct >= 50:
        st.warning(
            f"⚠️ Keskmine tulemus: **{pct}%** testidest läbitud ({n_passed}/{n_tests}). "
            f"RAG otsing või LLM vastused vajavad parandamist."
        )
    else:
        st.error(
            f"❌ Nõrk tulemus: ainult **{pct}%** testidest läbitud ({n_passed}/{n_tests}). "
            f"Süsteem vajab märkimisväärset parandamist."
        )

    st.dataframe(results_df, hide_index=True)
