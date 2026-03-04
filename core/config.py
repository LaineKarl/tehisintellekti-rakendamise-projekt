"""Rakenduse konstandid ja konfiguratsioon."""

MODEL_PRICES = {
    "google/gemma-3-27b-it":         {"input": 0.10,  "output": 0.20},
    "openai/gpt-4o-mini":            {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                 {"input": 5.00,  "output": 15.00},
    "anthropic/claude-3-haiku":      {"input": 0.25,  "output": 1.25},
    "mistralai/mistral-7b-instruct": {"input": 0.07,  "output": 0.07},
}

LOG_FILE = "data/tagasiside_log.csv"

LOG_COLUMNS = [
    "Aeg", "Kasutaja päring", "Filtrid", "Filtreeritud kursusi",
    "Leitud ID-d", "Leitud ained", "LLM Vastus", "Hinnang", "Viga sammus",
]

HINDAMISVIIS_MAP = {
    "Eristav":    "Eristav (A, B, C, D, E, F, mi)",
    "Eristamata": "Eristamata (arv, m.arv, mi)",
}

LINN_MAP = {
    "Tartu":    ["Tartu linn", "Tartu"],
    "Narva":    ["Narva linn"],
    "Viljandi": ["Viljandi linn"],
    "Pärnu":    ["Pärnu linn"],
    "Tõravere": ["Tõravere alevik"],
    "Tallinn":  ["Tallinn"],
}

DEFAULT_SESSION_STATE = {
    "messages": [],
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0,
}

ERROR_STEP_OPTIONS = [
    "",
    "Samm 1 – metaandmete filtreerimine (filtrid liiga karmid/valed)",
    "Samm 2 – RAG vektorotsing (leiti valed ained)",
    "Samm 3 – LLM vastuse genereerimine (hallutsinatsioon / vale vastus)",
]

RAG_DISPLAY_COLS = ["unique_ID", "nimi_et", "eap", "semester", "oppeaste", "score"]
