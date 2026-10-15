"""Compact labels for campaign plots; full run IDs remain in data summaries."""
from __future__ import annotations

import re
from pathlib import Path

_MONTHS = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


def _number(token: str) -> str:
    return token.replace("p", ".")


def compact_run_label(run_name: str | Path) -> str:
    """Return a short, parameter-oriented label for crowded group figures."""
    name = Path(run_name).name
    lowered = name.lower()
    date = re.match(r"^(20\d{2})(\d{2})(\d{2})_", lowered)

    if "cdm" in lowered and "sidm" not in lowered:
        if date:
            month = _MONTHS.get(date.group(2), date.group(2))
            return f"CDM ({date.group(3)} {month})"
        return "CDM"
    if "sidm" not in lowered:
        return name

    model = "dSIDM" if "dsidm" in lowered else "SIDM"
    sigma_match = re.search(r"(?:^|_)s(\d+(?:p\d+)?)(?:_|$)", lowered)
    sigma = _number(sigma_match.group(1)) if sigma_match else None
    label = model + (f" σ={sigma}" if sigma is not None else "")

    f_match = re.search(r"(?:^|_)fdiss(\d+(?:p\d+)?)(?:_|$)", lowered)
    d_match = re.search(r"(?:^|_)d(\d+(?:p\d+)?)(?:_|$)", lowered)
    if model == "dSIDM" and f_match:
        label += f", f={_number(f_match.group(1))}"
    elif d_match:
        label += f", D={_number(d_match.group(1))}"
    elif f_match:
        label += f", diss={_number(f_match.group(1))}"
    elif "elastic" in lowered or not f_match:
        label += " (elastic)"

    return label
