#!/bin/bash
# Batch script for SIDM and CDM runs (1 M particles each)
# Default mode is actual execution.
# Set DRY_RUN=1 to only print commands without running them.

DRY_RUN=0

# List of SIDM cross‑section values (σ)
SIGMAS=(0.1 1 2 5)

# Paths to the GalIC JSON configuration files
SIDM_CFG="ics/sidm_N1e6.json"
CDM_CFG="ics/cdm_N1e6.json"

# ----------------------------------------------------------------------
# Function: generate ICs using generate_ics.sh
# ----------------------------------------------------------------------
generate_ics() {
    local cfg=$1
    echo "Generating ICs for ${cfg} ..."
    if [ $DRY_RUN -eq 0 ]; then
        scripts/generate_ics.sh --config "${cfg}"
    else
        echo "DRY RUN: scripts/generate_ics.sh --config ${cfg}"
    fi
}

# ----------------------------------------------------------------------
# Generate ICs for SIDM and CDM (if not already present)
# ----------------------------------------------------------------------
generate_ics "$SIDM_CFG"
generate_ics "$CDM_CFG"

# Paths to the generated HDF5 files (without the .hdf5 suffix)
SIDM_IC="ics/sidm_N1e6/sidm_N1e6"
CDM_IC="ics/cdm_N1e6/cdm_N1e6"

# ----------------------------------------------------------------------
# Function: run a single GIZMO simulation via run_sim.sh
# ----------------------------------------------------------------------
run_simulation() {
    local run_name=$1   # e.g. sidm_sigma0.1_N1e6
    local sim_type=$2   # cdm or sidm
    local sigma=$3      # optional, only for SIDM
    local ic_path=$4    # path to IC file without .hdf5

    local run_dir="runs/${run_name}"
    mkdir -p "${run_dir}"

    # Copy the generic run wrapper
    cp scripts/run_sim.sh "${run_dir}/"

    # Choose the appropriate GIZMO parameter file
    if [ "$sim_type" = "sidm" ]; then
        cp gizmo_test/gizmo_sidm.param "${run_dir}/.gizmo_run.param"
        # Patch the SIDM cross‑section
        sed -i "s/DM_InteractionCrossSection.*/DM_InteractionCrossSection    ${sigma}/" "${run_dir}/.gizmo_run.param"
    else
        cp gizmo_test/gizmo_cdm.param "${run_dir}/.gizmo_run.param"
    fi

    # Execute (or echo) the simulation command
    if [ $DRY_RUN -eq 0 ]; then
        (cd "${run_dir}" && bash run_sim.sh --name "${run_name}" --type "${sim_type}" --ic-file "${ic_path}" ${sigma:+--sigma "${sigma}"})
    else
        echo "DRY RUN: cd ${run_dir} && bash run_sim.sh --name ${run_name} --type ${sim_type} --ic-file ${ic_path} ${sigma:+--sigma ${sigma}}"
    fi
}

# ----------------------------------------------------------------------
# SIDM runs for each sigma value
# ----------------------------------------------------------------------
for sigma in "${SIGMAS[@]}"; do
    RUN_NAME="sidm_sigma${sigma}_N1e6"
    run_simulation "$RUN_NAME" "sidm" "$sigma" "$SIDM_IC"
done

# ----------------------------------------------------------------------
# CDM control run
# ----------------------------------------------------------------------
run_simulation "cdm_N1e6" "cdm" "" "$CDM_IC"

# ----------------------------------------------------------------------
# Post‑processing: run halo analysis (dry‑run prints commands)
# ----------------------------------------------------------------------
for sigma in "${SIGMAS[@]}"; do
    SIDM_DIR="runs/sidm_sigma${sigma}_N1e6"
    CDM_DIR="runs/cdm_N1e6"
    if [ $DRY_RUN -eq 0 ]; then
        python3 scripts/analyze_halo.py --cdm "${CDM_DIR}" --sidm "${SIDM_DIR}" --rcore 50
    else
        echo "DRY RUN: python3 scripts/analyze_halo.py --cdm ${CDM_DIR} --sidm ${SIDM_DIR} --rcore 50"
    fi
done
