#!/usr/bin/env python3
"""plots/ic — блок ic реестра: gate-профиль начальных условий.

Математика/оформление дословно из check_ic_cusp.py (3 панели: density,
local slope, radial resolution). Данные — plot-ready dict из
loaders/ic.prepare_ic_figure_data() (читает ic_profiles.csv) или напрямую:
r_kpc, rho_meas, count, rho_nfw_target, slope_meas, slope_target.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis.base import (
    BasePlot,
    FieldSpec as F,
    validate_fields,
)
from analysis.registry import register


@register
class ICGateProfilePlot(BasePlot):
    name = "ic_gate_profile"
    block = "ic"
    summary = "IC-gate: измеренный профиль vs NFW-target + наклон + разрешение"
    data_source = "prepare_ic_figure_data"
    inputs = ("ic",)
    runner = "runners/make_ic_plots.py"
    description = (
        "Три панели IC-gate (как в check_ic_cusp.py): rho_meas vs rho_target "
        "(gate-диапазон подсвечен), локальный наклон vs target с опорой -1.0, "
        "частиц на бин с порогом nmin. Данные — ic_profiles.csv гейта."
    )
    data_contract = {
        "r_kpc": F(("R",)),
        "rho_meas": F(("R",)),
        "count": F(("R",)),
        "rho_nfw_target": F(("R",), required=False),
        "slope_meas": F(("R",), required=False),
        "slope_target": F(("R",), required=False),
    }
    default_config = {
        "title": "IC cusp resolution gate",
        "gate_range": (0.3, 3.0),
        "nmin": 200,
        "dpi": 130,
        "figsize": (15, 4.5),
        "filename": "ic_gate_profile.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        centers = np.asarray(data["r_kpc"], dtype=float)
        rho = np.asarray(data["rho_meas"], dtype=float)
        cnt = np.asarray(data["count"], dtype=float)
        rlo, rhi = config.get("gate_range", (0.3, 3.0))
        fig, ax = plt.subplots(1, 3, figsize=tuple(config.get("figsize", (15, 4.5))))
        good = (rho > 0) & (cnt > 0)
        ax[0].loglog(centers[good], rho[good], "o-", ms=3,
                     label="GalIC IC (measured)")
        if data.get("rho_nfw_target") is not None:
            rho_t = np.asarray(data["rho_nfw_target"], dtype=float)
            ax[0].loglog(centers, rho_t, "k--",
                         label="target (NFW fit to rotcurve)")
        ax[0].axvspan(rlo, rhi, color="0.85", alpha=0.5, label="gate range")
        ax[0].set_xlabel("r [kpc]")
        ax[0].set_ylabel("rho [1e10 Msun/kpc^3]")
        ax[0].legend(fontsize=8)
        ax[0].set_title("density profile")
        if data.get("slope_meas") is not None:
            ax[1].semilogx(centers, np.asarray(data["slope_meas"], dtype=float),
                           "o-", ms=3, label="measured")
        if data.get("slope_target") is not None:
            ax[1].semilogx(centers, np.asarray(data["slope_target"], dtype=float),
                           "k--", label="target")
        ax[1].axhline(-1.0, color="r", ls=":", lw=1)
        ax[1].axvspan(rlo, rhi, color="0.85", alpha=0.5)
        ax[1].set_xlabel("r [kpc]")
        ax[1].set_ylabel("d log rho / d log r")
        ax[1].legend(fontsize=8)
        ax[1].set_title("local logarithmic slope")
        ax[2].loglog(centers, cnt, "o-", ms=3)
        ax[2].axhline(config.get("nmin", 200), color="r", ls=":")
        ax[2].axvspan(rlo, rhi, color="0.85", alpha=0.5)
        ax[2].set_xlabel("r [kpc]")
        ax[2].set_ylabel("particles per bin")
        ax[2].set_title("radial resolution")
        fig.suptitle(config.get("title", ""))
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path
