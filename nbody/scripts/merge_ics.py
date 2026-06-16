#!/usr/bin/env python3
"""
merge_ics.py — универсальный конвертер и мерджер начальных условий (IC) для GIZMO.

Принимает JSON-конфиг и:
- читает HDF5-снапшоты GalIC (все в PartType1)
- конвертирует каждую компоненту в указанный PartType
- объединяет в один выходной HDF5-файл

Использование:
    python3 merge_ics.py <config.json>
"""
import json
import os
import sys
from pathlib import Path

import h5py
import numpy as np


def read_galic_snapshot(path: str) -> dict:
    """Читает GalIC HDF5-снапшот и возвращает dict с PartType1."""
    with h5py.File(path, "r") as f:
        data = {}
        if "PartType1" not in f:
            raise ValueError(f"PartType1 not found in {path}")
        pt = f["PartType1"]
        data["Coordinates"] = pt["Coordinates"][:]
        data["Velocities"] = pt["Velocities"][:]
        data["Masses"] = pt["Masses"][:]
        data["ParticleIDs"] = pt["ParticleIDs"][:]
        data["n_particles"] = len(data["Coordinates"])
        return data


def copy_group(src_file: h5py.File, src_key: str, dst_file: h5py.File, dst_key: str):
    """Копирует группу HDF5 из src в dst."""
    src_group = src_file[src_key]
    dst_group = dst_file.create_group(dst_key)
    for dataset_name in src_group:
        src_group.copy(dataset_name, dst_group)


def convert_and_merge(config: dict):
    """
    Основная логика:
    - Читает все input_file из компонент
    - Конвертирует PartType1 -> PartType<map_to>
    - Объединяет в один HDF5
    """
    output_dir = config["output_dir"]
    run_name = config["run_name"]
    components = config["components"]
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{run_name}.hdf5")
    header_attrs = {
        "num_files": 1,
        "flag_cooling": 0,
        "flag_stellar_age": 0,
        "flag_metals": 0,
        "flag_feedback": 0,
        "flag_sfr": 0,
        "HubbleParam": 1.0,
        "Redshift": 0.0,
        "BoxSize": 0.0,
    }

    total_npart = np.zeros(6, dtype=np.int32)
    com = np.zeros(3, dtype=np.float64)
    total_mass = 0.0

    with h5py.File(output_path, "w") as f:
        for comp in components:
            input_file = comp["input_file"]
            src_ptype = 1
            dst_ptype = comp["map_to"]
            comp_name = comp["name"]

            if not os.path.isfile(input_file):
                print(f"[ERROR] Input file not found: {input_file}")
                sys.exit(1)

            print(f"[INFO] Component '{comp_name}': {input_file} -> PartType{dst_ptype}")
            data = read_galic_snapshot(input_file)
            n = data["n_particles"]
            total_npart[dst_ptype] += n

            g = f.create_group(f"PartType{dst_ptype}")
            g.create_dataset("Coordinates", data=data["Coordinates"])
            g.create_dataset("Velocities", data=data["Velocities"])
            g.create_dataset("Masses", data=data["Masses"])
            g.create_dataset("ParticleIDs", data=data["ParticleIDs"])

            com += np.sum(data["Coordinates"] * data["Masses"][:, None], axis=0)
            total_mass += np.sum(data["Masses"])

            print(f"    {n} particles, PartType{dst_ptype}")

        if total_mass > 0:
            com /= total_mass

        header = f.create_group("Header")
        header.attrs["NumPart_Total"] = total_npart
        header.attrs["NumPart_ThisFile"] = total_npart.copy()
        header.attrs["NumPart_Total_HighWord"] = np.zeros(6, dtype=np.int32)
        header.attrs["MassTable"] = np.zeros(6, dtype=np.float64)
        header.attrs["Time"] = 0.0
        header.attrs["Redshift"] = 0.0
        header.attrs["BoxSize"] = 0.0
        header.attrs["HubbleParam"] = 1.0
        header.attrs["NumFilesPerSnapshot"] = 1
        header.attrs["UnitLength_In_CGS"] = 3.085678e21
        header.attrs["UnitMass_In_CGS"] = 1.989e43
        header.attrs["UnitVelocity_In_CGS"] = 1.0e5
        header.attrs["GIZMO_version"] = 2022

        if "sigma" in components[0]:
            header.attrs["DM_InteractionCrossSection"] = components[0]["sigma"]
        else:
            header.attrs["DM_InteractionCrossSection"] = 0.0

    print(f"\n[INFO] Output: {output_path}")
    print(f"[INFO] Total particles: {int(total_npart.sum())}")
    print(f"[INFO] COM offset: {np.linalg.norm(com):.4f}")
    return output_path


def find_galic_snapshot(galic_dir: str) -> str:
    """Находит последний HDF5-снапшот в директории GalIC."""
    candidates = []
    for f in os.listdir(galic_dir):
        if f.endswith(".hdf5") and not f.startswith("."):
            candidates.append(os.path.join(galic_dir, f))
    if not candidates:
        raise FileNotFoundError(f"No HDF5 snapshots found in {galic_dir}")
    candidates.sort(key=lambda p: os.path.getmtime(p))
    return candidates[-1]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    config_path = sys.argv[1]
    with open(config_path) as f:
        config = json.load(f)

    print(f"[INFO] run_name:     {config['run_name']}")
    print(f"[INFO] output_dir:   {config['output_dir']}")
    print(f"[INFO] components:   {len(config['components'])}")

    convert_and_merge(config)


if __name__ == "__main__":
    main()