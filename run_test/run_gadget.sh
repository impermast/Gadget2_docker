#!/bin/bash

echo "Running Gadget2 simulation..."
cp /workspace/Gadget-2.0.7/Gadget2/Gadget2 .
mpirun --allow-run-as-root -n 1 ./Gadget2 /workspace/run_test/lcdm_gas.param
GADGET_EXIT=$?

if [ $GADGET_EXIT -ne 0 ]; then
    echo "ERROR: Gadget2 failed with exit code $GADGET_EXIT"
    exit $GADGET_EXIT
fi

echo "Running visualization..."
python3 /workspace/run_test/example_snap.py
