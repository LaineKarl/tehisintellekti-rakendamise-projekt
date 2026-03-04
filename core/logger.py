"""Tagasiside ja päringutulemuste logimine CSV-faili."""

import csv
import os

from core.config import LOG_FILE, LOG_COLUMNS


def log_feedback(timestamp, prompt, filters, filtered_count,
                 context_ids, context_names, response, rating, error_step):
    """Salvestab ühe päringu tulemuse CSV logifaili."""
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(LOG_COLUMNS)
        writer.writerow([
            timestamp, prompt, filters, filtered_count,
            str(context_ids), str(context_names),
            response, rating, error_step,
        ])
