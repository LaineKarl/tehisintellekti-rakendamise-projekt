"""LLM-iga suhtlemine – süsteemiprompt ja streaming-vastus."""

import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # Laeb .env-faili keskkonnamuutujad

from core.data import estimate_tokens


def build_system_prompt(filter_desc: str, context_text: str) -> str:
    """Koostab süsteemiprompt'i LLM-ile."""
    return (
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


def stream_llm_response(model: str, system_prompt: str):
    """
    Saadab päringu LLM-ile ja kuvab streaming-vastust.

    Tagastab:
        (response_text, in_tok, out_tok)
    """
    system_msg = {"role": "system", "content": system_prompt}
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]
    messages_to_send = [system_msg] + chat_history
    input_tok_est = estimate_tokens(
        " ".join(m["content"] for m in messages_to_send)
    )

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("API_KEY"))
    stream = client.chat.completions.create(
        model=model,
        messages=messages_to_send,
        stream=True,
        stream_options={"include_usage": True},
    )

    response_text = ""
    usage_data = None
    placeholder = st.empty()

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            response_text += chunk.choices[0].delta.content
            placeholder.markdown(response_text + "▌")
        if hasattr(chunk, "usage") and chunk.usage:
            usage_data = chunk.usage

    placeholder.markdown(response_text)

    if usage_data and hasattr(usage_data, "prompt_tokens"):
        in_tok = usage_data.prompt_tokens
        out_tok = usage_data.completion_tokens
    else:
        in_tok = input_tok_est
        out_tok = estimate_tokens(response_text)

    return response_text, in_tok, out_tok
