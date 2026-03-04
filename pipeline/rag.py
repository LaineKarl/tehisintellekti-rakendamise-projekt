"""RAG vektorotsing – semantiline sarnasus embeddings-põhiselt."""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def perform_rag_search(embedder, query: str, filtered_df: pd.DataFrame, top_n: int):
    """
    Teostab vektorotsingu filtreeritud andmetel.

    Tagastab:
        (context_text, results_df_display)
    """
    if filtered_df.empty:
        return "Ühtegi kursust ei vasta valitud filtritele.", pd.DataFrame()

    query_vec = embedder.encode([query])[0]
    filtered_df["score"] = cosine_similarity(
        [query_vec], np.stack(filtered_df["embedding"])
    )[0]
    results_df = filtered_df.sort_values("score", ascending=False).head(top_n)
    display_df = results_df.drop(columns=["embedding"], errors="ignore").copy()
    context_text = results_df.drop(
        columns=["score", "embedding"], errors="ignore"
    ).to_string(index=False)
    return context_text, display_df
