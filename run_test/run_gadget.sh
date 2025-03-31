#!/bin/bash

echo "GADGET-2..."
cp /workspace/Gadget-2.0.7/Gadget2/Gadget2 .
mpirun --allows-run-as-root -n 1 ./Gadget2 /workspace/run_test/lcdm_gas.param

echo "Running visualization..."
python3 /workspace/run_test/example_snap.py
