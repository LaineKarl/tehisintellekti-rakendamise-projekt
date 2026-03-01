import streamlit as st
import pandas as pd
import numpy as np
import csv
import os
from datetime import datetime
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ─── KONFIGURATSIOON ───────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Kursuse Nõustaja", page_icon="🎓", layout="wide")

MODEL_PRICES = {
    "google/gemma-3-27b-it":         {"input": 0.10,  "output": 0.20},
    "openai/gpt-4o-mini":            {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                 {"input": 5.00,  "output": 15.00},
    "anthropic/claude-3-haiku":      {"input": 0.25,  "output": 1.25},
    "mistralai/mistral-7b-instruct": {"input": 0.07,  "output": 0.07},
}

LOG_FILE = "tagasiside_log.csv"

# ─── VAHESAMMUDE LOGIMINE ──────────────────────────────────────────────────────
# Kolm vahesammu: 1) metaandmete filtreerimine, 2) RAG vektorotsing, 3) LLM vastus

def log_feedback(timestamp, prompt, filters, filtered_count,
                 context_ids, context_names, response,
                 rating, error_step):
    """
    Salvestab ühe päringu tulemuse CSV logifaili.

    Veerud:
      Aeg | Kasutaja päring | Filtrid | Filtreeritud kursusi |
      Leitud ID-d | Leitud ained | LLM Vastus | Hinnang | Viga sammus
    """
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Aeg", "Kasutaja päring", "Filtrid",
                "Filtreeritud kursusi",
                "Leitud ID-d", "Leitud ained",
                "LLM Vastus", "Hinnang", "Viga sammus"
            ])
        writer.writerow([
            timestamp, prompt, filters, filtered_count,
            str(context_ids), str(context_names),
            response, rating, error_step
        ])

# ─── MUDELI JA ANDMETE LAADIMINE ──────────────────────────────────────────────
@st.cache_resource
def get_models():
    embedder = SentenceTransformer("BAAI/bge-m3")
    df = pd.read_csv("puhtad_andmed.csv")
    embeddings_df = pd.read_pickle("puhtad_andmed_embeddings.pkl")
    merged = pd.merge(df, embeddings_df, on="unique_ID")
    return embedder, merged

embedder, merged_df = get_models()

def get_unique_sorted(col):
    return sorted(merged_df[col].dropna().unique().tolist())

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def update_cost(in_tok, out_tok, model):
    prices = MODEL_PRICES.get(model, {"input": 0.0, "output": 0.0})
    cost = (in_tok * prices["input"] + out_tok * prices["output"]) / 1_000_000
    st.session_state.total_input_tokens  += in_tok
    st.session_state.total_output_tokens += out_tok
    st.session_state.total_cost_usd      += cost

# ─── SESSIOONIOLEKU INITSIALISEERIMINE ────────────────────────────────────────
for key, val in [
    ("messages", []),
    ("total_input_tokens", 0),
    ("total_output_tokens", 0),
    ("total_cost_usd", 0.0),
]:
    if key not in st.session_state:
        st.session_state[key] = val

# ─── PEALKIRI ─────────────────────────────────────────────────────────────────
st.title("🎓 AI Kursuse Nõustaja – Samm 7")
st.caption("RAG süsteem koos vahesammude logimise, kapotialuse analüüsi, tagasiside ja vigade analüüsiga.")

# ─── KÜLGRIBA ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Seaded")
    api_key = st.text_input("OpenRouter API Key", type="password")
    selected_model = st.selectbox("Mudel", list(MODEL_PRICES.keys()))

    st.divider()
    st.subheader("🔍 Metaandmete filtrid")
    st.caption("Jäta tühjaks, kui filter pole oluline.")

    semesters = ["(kõik)"] + get_unique_sorted("semester")
    sel_semester = st.selectbox("Semester", semesters)

    eap_values = ["(kõik)"] + [str(v) for v in get_unique_sorted("eap")]
    sel_eap = st.selectbox("EAP maht", eap_values)

    if "language" in merged_df.columns:
        langs = ["(kõik)"] + get_unique_sorted("language")
        sel_lang = st.selectbox("Keel", langs)
    else:
        sel_lang = "(kõik)"

    hindamis_opts = st.multiselect("Hindamisviis", ["Eristav", "Eristamata"])
    linn_opts     = st.multiselect("Linn", ["Tartu", "Tallinn", "Narva", "Pärnu", "Viljandi", "Tõravere"])
    aste_opts     = st.multiselect("Õppeaste", ["bakalaureuse", "magistri", "doktori"])
    veeb_opts     = st.multiselect("Õppevorm", ["põimõpe", "lähiõpe", "veebiõpe"])
    no_prereqs    = st.checkbox("Ainult ilma eeldusaineteta kursused")
    results_N     = st.slider("Kuvatavate kursuste arv (Top-N)", 1, 20, 5)

    st.divider()
    st.subheader("💰 Kulu jälgimine")
    col_a, col_b = st.columns(2)
    col_a.metric("Sisend-tokenid", f"{st.session_state.total_input_tokens:,}")
    col_b.metric("Väljund-tokenid", f"{st.session_state.total_output_tokens:,}")
    st.metric("Jooksev kulu (USD)", f"${st.session_state.total_cost_usd:.6f}")

    if st.button("🔄 Nulli vestlus ja kulu"):
        st.session_state.messages = []
        st.session_state.total_input_tokens  = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost_usd      = 0.0
        st.rerun()

    st.divider()
    st.subheader("📊 Vigade analüüs")
    if st.button("Näita vigade analüüsi"):
        st.session_state.show_analysis = True

# ─── VIGADE ANALÜÜS (eraldi lehel/sektsioonis) ────────────────────────────────
if st.session_state.get("show_analysis", False):
    st.subheader("📊 Vigade analüüs logist")
    if os.path.isfile(LOG_FILE):
        log_df = pd.read_csv(LOG_FILE)
        total  = len(log_df)
        bad    = log_df[log_df["Hinnang"] == "👎 Halb"]
        n_bad  = len(bad)

        st.write(f"**Kokku päringuid:** {total} | **Halbu vastuseid:** {n_bad}")

        if n_bad > 0:
            step_counts = bad["Viga sammus"].value_counts().reset_index()
            step_counts.columns = ["Vahesamm", "Vigade arv"]
            step_counts["% kõikidest vigadest"] = (step_counts["Vigade arv"] / n_bad * 100).round(1)

            st.write("**Vigade jaotus vahesammude kaupa:**")
            st.dataframe(step_counts, hide_index=True)

            # Veergdiagramm
            st.bar_chart(step_counts.set_index("Vahesamm")["Vigade arv"])

            st.write("**Halvad juhtumid detailidega:**")
            cols_show = [c for c in ["Aeg", "Kasutaja päring", "Filtrid",
                                     "Filtreeritud kursusi", "Viga sammus"] if c in bad.columns]
            st.dataframe(bad[cols_show], hide_index=True)
        else:
            st.success("Logis ei ole ühtegi halba vastust – suurepärane!")
    else:
        st.info("Logifaili pole veel loodud. Tee mõned päringud ja anna tagasisidet.")

    if st.button("Sulge analüüs"):
        st.session_state.show_analysis = False
        st.rerun()

st.divider()

# ─── VESTLUSAJALUGU ───────────────────────────────────────────────────────────
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and "debug_info" in message:
            debug = message["debug_info"]

            # ── VAHESAMM 1: Metaandmete filtreerimine ──
            with st.expander("🔍 Vahesamm 1 – Metaandmete filtreerimine"):
                st.caption(f"**Aktiivsed filtrid:** {debug.get('filters', '–')}")
                fc = debug.get("filtered_count", 0)
                st.write(f"Filtrid jätsid andmestikku alles **{fc}** kursust.")
                if fc == 0:
                    st.warning("⚠️ Ükski kursus ei vastanud filtritele – kontekst on tühi!")

            # ── VAHESAMM 2: RAG vektorotsing ──
            with st.expander("🔍 Vahesamm 2 – RAG vektorotsing (Top-N tulemused)"):
                ctx_df = debug.get("context_df", pd.DataFrame())
                if not ctx_df.empty:
                    display_cols = ["unique_ID", "nimi_et", "eap", "semester", "oppeaste", "score"]
                    cols_to_show = [c for c in display_cols if c in ctx_df.columns]
                    st.dataframe(ctx_df[cols_to_show], hide_index=True)
                else:
                    st.warning("Ühtegi kursust ei leitud.")

            # ── VAHESAMM 3: LLM süsteemiviip ──
            with st.expander("🔍 Vahesamm 3 – LLM-ile saadetud süsteemiviip"):
                st.text_area(
                    "Täpne prompt LLM-ile:",
                    debug.get("system_prompt", ""),
                    height=160,
                    disabled=True,
                    key=f"prompt_area_{i}",
                )

            # ── TAGASISIDE ──
            with st.expander("📝 Hinda vastust (salvestab logisse)"):
                with st.form(key=f"feedback_form_{i}"):
                    rating = st.radio(
                        "Hinnang vastusele:", ["👍 Hea", "👎 Halb"],
                        horizontal=True, key=f"rating_{i}"
                    )
                    error_step = st.selectbox(
                        "Kui vastus oli halb – mis samm põhjustas vea?",
                        [
                            "",
                            "Samm 1 – metaandmete filtreerimine (filtrid liiga karmid/valed)",
                            "Samm 2 – RAG vektorotsing (leiti valed ained)",
                            "Samm 3 – LLM vastuse genereerimine (hallutsinatsioon / vale vastus)",
                        ],
                        key=f"kato_{i}",
                    )
                    if st.form_submit_button("Salvesta hinnang"):
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ctx_df = debug.get("context_df", pd.DataFrame())
                        ctx_ids   = ctx_df["unique_ID"].tolist() if not ctx_df.empty else []
                        name_col  = next((c for c in ["nimi_et", "aine_nimetus_est"] if c in ctx_df.columns), None)
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

# ─── PEAMINE SISEND ───────────────────────────────────────────────────────────
if prompt := st.chat_input("Kirjelda, mida soovid õppida..."):

    # Filtrite tekstiline kirjeldus
    active_filters = []
    if sel_semester != "(kõik)": active_filters.append(f"semester={sel_semester}")
    if sel_eap      != "(kõik)": active_filters.append(f"EAP={sel_eap}")
    if sel_lang     != "(kõik)": active_filters.append(f"keel={sel_lang}")
    if hindamis_opts: active_filters.append(f"hindamisviis={hindamis_opts}")
    if linn_opts:     active_filters.append(f"linn={linn_opts}")
    if aste_opts:     active_filters.append(f"aste={aste_opts}")
    if veeb_opts:     active_filters.append(f"veeb={veeb_opts}")
    if no_prereqs:    active_filters.append("eeldusaineteta=True")
    filter_desc = ", ".join(active_filters) if active_filters else "pole (kõik kursused)"

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            err = "⚠️ Palun sisesta API võti külgribal!"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
        else:
            with st.spinner("Otsin sobivaid kursusi..."):

                # ── VAHESAMM 1: Metaandmete filtreerimine ─────────────────────
                mask = pd.Series([True] * len(merged_df), index=merged_df.index)

                if sel_semester != "(kõik)":
                    mask &= merged_df["semester"] == sel_semester
                if sel_eap != "(kõik)":
                    mask &= merged_df["eap"] == float(sel_eap)
                if sel_lang != "(kõik)" and "language" in merged_df.columns:
                    mask &= merged_df["language"] == sel_lang
                if hindamis_opts:
                    hind_map = {
                        "Eristav":    "Eristav (A, B, C, D, E, F, mi)",
                        "Eristamata": "Eristamata (arv, m.arv, mi)",
                    }
                    mask &= merged_df["hindamisviis"].isin([hind_map[h] for h in hindamis_opts])
                if linn_opts:
                    linn_mask = pd.Series(False, index=merged_df.index)
                    if "Tartu"    in linn_opts: linn_mask |= merged_df["linn"].isin(["Tartu linn", "Tartu"]) | merged_df["linn"].isna()
                    if "Narva"    in linn_opts: linn_mask |= (merged_df["linn"] == "Narva linn")
                    if "Viljandi" in linn_opts: linn_mask |= (merged_df["linn"] == "Viljandi linn")
                    if "Pärnu"    in linn_opts: linn_mask |= (merged_df["linn"] == "Pärnu linn")
                    if "Tõravere" in linn_opts: linn_mask |= (merged_df["linn"] == "Tõravere alevik")
                    if "Tallinn"  in linn_opts: linn_mask |= (merged_df["linn"] == "Tallinn")
                    mask &= linn_mask
                if aste_opts:
                    pattern = "|".join(aste_opts)
                    mask &= merged_df["oppeaste"].str.contains(pattern, case=False, na=False)
                if veeb_opts:
                    mask &= merged_df["veebiope"].isin(veeb_opts)
                if no_prereqs:
                    mask &= merged_df["eeldusained"].isna()

                filtered_df    = merged_df[mask].copy()
                filtered_count = len(filtered_df)

                # ── VAHESAMM 2: RAG vektorotsing ──────────────────────────────
                if filtered_df.empty:
                    context_text      = "Ühtegi kursust ei vasta valitud filtritele."
                    results_df_display = pd.DataFrame()
                    st.warning(context_text)
                else:
                    query_vec = embedder.encode([prompt])[0]
                    filtered_df["score"] = cosine_similarity(
                        [query_vec], np.stack(filtered_df["embedding"])
                    )[0]
                    results_df = (
                        filtered_df.sort_values("score", ascending=False)
                        .head(results_N)
                    )
                    results_df_display = results_df.drop(columns=["embedding"], errors="ignore").copy()
                    context_text = results_df.drop(columns=["score", "embedding"], errors="ignore").to_string(index=False)

                # ── VAHESAMM 3: LLM vastuse genereerimine ─────────────────────
                system_prompt_content = (
                    "Oled ülikoolikursuste nõustaja. Sinu ainus ülesanne on aidata kasutajal leida "
                    "ja valida sobivaid ülikoolikursusi. "
                    "Sa ei aruta kunagi muid teemasid – kui kasutaja küsib millegi muu kohta, "
                    "vasta lühidalt ja viisakalt, et saad nõustada ainult ülikoolikursuste osas.\n\n"
                    f"Kasutatud filtrid: {filter_desc}.\n\n"
                    "Allpool on semantilise otsingu põhjal leitud sobivaimad kursused:\n\n"
                    f"{context_text}\n\n"
                    "Vasta eesti keeles. Ole konkreetne ja abivalmis. "
                    "Viita ainult ülaltoodud kursustele."
                )
                system_prompt_msg = {"role": "system", "content": system_prompt_content}
                messages_to_send  = [system_prompt_msg] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]

                input_tok_est = estimate_tokens(" ".join(m["content"] for m in messages_to_send))

                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
                try:
                    stream = client.chat.completions.create(
                        model=selected_model,
                        messages=messages_to_send,
                        stream=True,
                        stream_options={"include_usage": True},
                    )

                    response_text = ""
                    usage_data    = None
                    placeholder   = st.empty()

                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            response_text += chunk.choices[0].delta.content
                            placeholder.markdown(response_text + "▌")
                        if hasattr(chunk, "usage") and chunk.usage:
                            usage_data = chunk.usage

                    placeholder.markdown(response_text)

                    if usage_data and hasattr(usage_data, "prompt_tokens"):
                        in_tok  = usage_data.prompt_tokens
                        out_tok = usage_data.completion_tokens
                    else:
                        in_tok  = input_tok_est
                        out_tok = estimate_tokens(response_text)

                    update_cost(in_tok, out_tok, selected_model)

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
                            "filtered_count": filtered_count,
                            "context_df":     results_df_display,
                            "system_prompt":  system_prompt_content,
                        },
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Viga API päringul: {e}")