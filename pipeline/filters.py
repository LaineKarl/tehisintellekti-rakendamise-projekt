"""Metaandmete filtrite koostamine ja rakendamine."""

import pandas as pd

from core.config import HINDAMISVIIS_MAP, LINN_MAP


def build_filter_description(filters_cfg: dict) -> str:
    """Koostab filtrite tekstilise kirjelduse logimiseks/kuva jaoks."""
    parts = []
    if filters_cfg["semester"] != "(kõik)":
        parts.append(f"semester={filters_cfg['semester']}")
    if filters_cfg["eap"] != "(kõik)":
        parts.append(f"EAP={filters_cfg['eap']}")
    if filters_cfg["lang"] != "(kõik)":
        parts.append(f"keel={filters_cfg['lang']}")
    if filters_cfg["hindamisviis"]:
        parts.append(f"hindamisviis={filters_cfg['hindamisviis']}")
    if filters_cfg["linn"]:
        parts.append(f"linn={filters_cfg['linn']}")
    if filters_cfg["aste"]:
        parts.append(f"aste={filters_cfg['aste']}")
    if filters_cfg["veeb"]:
        parts.append(f"veeb={filters_cfg['veeb']}")
    if filters_cfg["no_prereqs"]:
        parts.append("eeldusaineteta=True")
    return ", ".join(parts) if parts else "pole (kõik kursused)"


def apply_metadata_filters(df: pd.DataFrame, filters_cfg: dict) -> pd.DataFrame:
    """Rakendab kasutaja valitud metaandmete filtrid ja tagastab filtreeritud DataFrame'i."""
    mask = pd.Series(True, index=df.index)

    if filters_cfg["semester"] != "(kõik)":
        mask &= df["semester"] == filters_cfg["semester"]
    if filters_cfg["eap"] != "(kõik)":
        mask &= df["eap"] == float(filters_cfg["eap"])
    if filters_cfg["lang"] != "(kõik)" and "language" in df.columns:
        mask &= df["language"] == filters_cfg["lang"]
    if filters_cfg["hindamisviis"]:
        mapped = [HINDAMISVIIS_MAP[h] for h in filters_cfg["hindamisviis"]]
        mask &= df["hindamisviis"].isin(mapped)
    if filters_cfg["linn"]:
        linn_mask = pd.Series(False, index=df.index)
        for linn in filters_cfg["linn"]:
            values = LINN_MAP.get(linn, [])
            linn_mask |= df["linn"].isin(values)
            if linn == "Tartu":
                linn_mask |= df["linn"].isna()
        mask &= linn_mask
    if filters_cfg["aste"]:
        pattern = "|".join(filters_cfg["aste"])
        mask &= df["oppeaste"].str.contains(pattern, case=False, na=False)
    if filters_cfg["veeb"]:
        mask &= df["veebiope"].isin(filters_cfg["veeb"])
    if filters_cfg["no_prereqs"]:
        mask &= df["eeldusained"].isna()

    return df[mask].copy()
