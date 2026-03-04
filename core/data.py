"""Andmete laadimine, token-hinnangud ja kulu jälgimine."""

import streamlit as st
import pandas as pd
from sentence_transformers import SentenceTransformer

from core.config import MODEL_PRICES


@st.cache_resource
def load_data():
    """Laeb embedderi, CSV-andmed ja embeddings-pickle'i ning ühendab need."""
    embedder = SentenceTransformer("BAAI/bge-m3")
    df = pd.read_csv("data/puhtad_andmed.csv")
    embeddings_df = pd.read_pickle("data/puhtad_andmed_embeddings.pkl")
    merged = pd.merge(df, embeddings_df, on="unique_ID")
    return embedder, merged


def get_unique_sorted(df, col):
    """Tagastab veeru unikaalsed väärtused sordituna."""
    return sorted(df[col].dropna().unique().tolist())


def estimate_tokens(text: str) -> int:
    """Ligikaudne tokenite arvu hinnang (1 token ≈ 4 tähemärki)."""
    return max(1, len(text) // 4)


def update_cost(in_tok: int, out_tok: int, model: str):
    """Uuendab sessiooni kulu- ja tokeniloendurit."""
    prices = MODEL_PRICES.get(model, {"input": 0.0, "output": 0.0})
    cost = (in_tok * prices["input"] + out_tok * prices["output"]) / 1_000_000
    st.session_state.total_input_tokens  += in_tok
    st.session_state.total_output_tokens += out_tok
    st.session_state.total_cost_usd      += cost
