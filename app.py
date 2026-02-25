import streamlit as st
import pandas as pd
import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ─── Lehe seaded ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Kursuse Nõustaja", page_icon="🎓", layout="wide")
st.title("🎓 AI Kursuse Nõustaja")
st.caption("RAG süsteem koos metaandmete filtreerimise ja vestlusajalooga.")

# ─── Mudeli valik & hinnad (USD / 1M token) ────────────────────────────────────
MODEL_PRICES = {
    "google/gemma-3-27b-it":      {"input": 0.10,  "output": 0.20},
    "openai/gpt-4o-mini":         {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":              {"input": 5.00,  "output": 15.00},
    "anthropic/claude-3-haiku":   {"input": 0.25,  "output": 1.25},
    "mistralai/mistral-7b-instruct": {"input": 0.07, "output": 0.07},
}

# ─── Sessioonioleku initsialiseerimine ────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0
if "total_cost_usd" not in st.session_state:
    st.session_state.total_cost_usd = 0.0
if "rag_done" not in st.session_state:
    st.session_state.rag_done = False   # kas RAG otsing on tehtud

# ─── Andmete laadimine ────────────────────────────────────────────────────────
@st.cache_resource
def get_models():
    embedder = SentenceTransformer("BAAI/bge-m3")
    df = pd.read_csv("puhtad_andmed.csv")
    embeddings_df = pd.read_pickle("puhtad_andmed_embeddings.pkl")
    merged = pd.merge(df, embeddings_df, on="unique_ID")
    return embedder, merged

embedder, merged_df = get_models()

# ─── Abilised ─────────────────────────────────────────────────────────────────
def get_unique_sorted(col):
    """Tagastab veerus olevad unikaalsed mitte-null väärtused sorteeritult."""
    return sorted(merged_df[col].dropna().unique().tolist())

def estimate_tokens(text: str) -> int:
    """Lihtne tokenite arvu hinnang (≈4 tähemärki / token)."""
    return max(1, len(text) // 4)

def update_cost(input_tok: int, output_tok: int, model: str):
    prices = MODEL_PRICES.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tok * prices["input"] + output_tok * prices["output"]) / 1_000_000
    st.session_state.total_input_tokens  += input_tok
    st.session_state.total_output_tokens += output_tok
    st.session_state.total_cost_usd      += cost

# ─── Külgriba ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Seaded")
    api_key = st.text_input("OpenRouter API Key", type="password")
    selected_model = st.selectbox("Mudel", list(MODEL_PRICES.keys()))

    st.divider()
    st.subheader("🔍 Metaandmete filtrid")
    st.caption("Jäta tühjaks, kui filter pole oluline.")

    # Semester
    semesters = ["(kõik)"] + get_unique_sorted("semester")
    sel_semester = st.selectbox("Semester", semesters)

    # EAP (mahuühik)
    eap_values = ["(kõik)"] + [str(v) for v in get_unique_sorted("eap")]
    sel_eap = st.selectbox("EAP maht", eap_values)

    # Keel (kui veerg olemas)
    if "language" in merged_df.columns:
        langs = ["(kõik)"] + get_unique_sorted("language")
        sel_lang = st.selectbox("Keel", langs)
    else:
        sel_lang = "(kõik)"

    # Tulemuste arv
    results_N = st.slider("Kuvatavate kursuste arv (Top-N)", 1, 20, 5)

    st.divider()
    st.subheader("💰 Kulu jälgimine")
    col_a, col_b = st.columns(2)
    col_a.metric("Sisend-tokenid", f"{st.session_state.total_input_tokens:,}")
    col_b.metric("Väljund-tokenid", f"{st.session_state.total_output_tokens:,}")
    st.metric("Jooksev kulu (USD)", f"${st.session_state.total_cost_usd:.6f}")

    if st.button("🔄 Nulli vestlus ja kulu"):
        st.session_state.messages = []
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost_usd = 0.0
        st.session_state.rag_done = False
        st.rerun()

# ─── Vestlusajalugu ───────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ─── Peamine sisend ───────────────────────────────────────────────────────────
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            error_msg = "⚠️ Palun sisesta API võti külgribal!"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            # ── RAG: teeme ainult esimesel päringul (või kui filtrid muutuvad) ──
            # Tegelikult teeme RAGi iga kord, kuid RAG konteksti hoiame süsteemisõnumis.
            # Nii saab vestlus jätkuda ilma uue otsinguta.

            with st.spinner("Otsin sobivaid kursusi..."):

                # 1. Rakenda filtrid
                mask = pd.Series([True] * len(merged_df), index=merged_df.index)

                if sel_semester != "(kõik)":
                    mask &= merged_df["semester"] == sel_semester
                if sel_eap != "(kõik)":
                    mask &= merged_df["eap"] == float(sel_eap)
                if sel_lang != "(kõik)" and "language" in merged_df.columns:
                    mask &= merged_df["language"] == sel_lang

                filtered_df = merged_df[mask].copy()

                # 2. Semantiline otsing filtreeritud andmestiku peal
                if filtered_df.empty:
                    context_text = "Ühtegi kursust ei vasta valitud filtritele."
                    st.warning(context_text)
                else:
                    query_vec = embedder.encode([prompt])[0]
                    filtered_df["score"] = cosine_similarity(
                        [query_vec], np.stack(filtered_df["embedding"])
                    )[0]
                    results_df = (
                        filtered_df.sort_values("score", ascending=False)
                        .head(results_N)
                        .drop(["score", "embedding"], axis=1)
                    )

                

                    context_text = results_df.to_string(index=False)

            # 3. Koosta süsteemisõnum koos RAG kontekstiga
            # Rakendame aktiivseid filtreid
            active_filters = []
            if sel_semester != "(kõik)":  active_filters.append(f"semester={sel_semester}")
            if sel_eap      != "(kõik)":  active_filters.append(f"EAP={sel_eap}")
            if sel_lang     != "(kõik)":  active_filters.append(f"keel={sel_lang}")
            filter_desc = ", ".join(active_filters) if active_filters else "pole (kõik kursused)"

            system_prompt = {
                "role": "system",
                "content": (
                    "Oled ülikoolikursuste nõustaja. Sinu ainus ülesanne on aidata kasutajal leida ja valida sobivaid ülikoolikursusi. "
                    "Sa ei aruta kunagi muid teemasid – kui kasutaja küsib millegi muu kohta (nt üldised eluküsimused, poliitika, tehnoloogia, isiklikud teemad vms), "
                    "siis vasta lühidalt ja viisakalt, et saad nõustada ainult ülikoolikursuste osas, ning suuna vestlus tagasi kursuste teemale.\n\n"
                    f"Kasutatud filtrid: {filter_desc}.\n\n"
                    "Allpool on semantilise otsingu põhjal leitud sobivaimad kursused:\n\n"
                    f"{context_text}\n\n"
                    "Vasta eesti keeles. Ole konkreetne ja abivalmis. "
                    "Viita ainult ülaltoodud kursustele."
                ),
            }

            messages_to_send = [system_prompt] + st.session_state.messages

            # 4. Tokenite hinnang sisendile (enne vastust)
            input_text = " ".join(m["content"] for m in messages_to_send)
            input_tok_est = estimate_tokens(input_text)

            # 5. LLM vastus (streaming)
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            try:
                stream = client.chat.completions.create(
                    model=selected_model,
                    messages=messages_to_send,
                    stream=True,
                    stream_options={"include_usage": True},  # OpenRouter toetab
                )

                response_text = ""
                usage_data = None

                # Käsitsi stream töötlus, et saada usage
                placeholder = st.empty()
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                        placeholder.markdown(response_text + "▌")
                    # Mõned mudelid saadavad usage viimases chunks
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_data = chunk.usage

                placeholder.markdown(response_text)

                # 6. Uuenda tokenite arvestust
                if usage_data and hasattr(usage_data, "prompt_tokens"):
                    in_tok  = usage_data.prompt_tokens
                    out_tok = usage_data.completion_tokens
                else:
                    # Hinnang, kui API ei tagasta usage andmeid
                    in_tok  = input_tok_est
                    out_tok = estimate_tokens(response_text)

                update_cost(in_tok, out_tok, selected_model)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

                # Kuva tokenite info sõnumi all
                st.caption(
                    f"🔢 See päring: {in_tok:,} sisend + {out_tok:,} väljund tokenit | "
                    f"Kokku kulu: ${st.session_state.total_cost_usd:.6f}"
                )

            except Exception as e:
                st.error(f"Viga API päringul: {e}")