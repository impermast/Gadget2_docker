# Dockerized GADGET-2 and GIZMO Environment

This repository provides a Docker-based environment for building and running cosmological N-body/SPH simulations with **GADGET-2** and **GIZMO**.

The environment is designed for flexibility, allowing you to compile the simulation codes at runtime with custom configurations without needing to rebuild the entire Docker image.

---

## Features

- **Reproducible Environment:** Includes Ubuntu 20.04 with all necessary scientific libraries (MPI, GSL 1.16, FFTW 2.1.5, HDF5).
- **Flexible Compilation:** Compile GADGET-2 and GIZMO at runtime using simple shell scripts.
- **Parallel Ready:** `mpicc` and `mpirun` are configured and ready to use.
- **GIZMO & GADGET-2:** Contains the source code for both simulation packages.
- **Helper Tools:** Includes Python 3, `numpy`, `matplotlib`, `pandas`, and the `glio` visualization library.

---

## How to Build the Image

From the root of the project directory, run:

```bash
docker build -t gadget2 .
```

---

## How to Run Simulations

### 1. Start the Container

Run the container interactively using the provided script. This script handles mounting the `dockerData` directory for simulation outputs and enables GUI applications.

```bash
./run_docker_gui_linux.sh
```

This script will start a container named `gadget2`. If a container with that name already exists, it will simply start it.

### 2. Execute a Simulation

The environment uses a special workflow. You do not run the simulation code directly. Instead, you use wrapper scripts that first compile the code with your desired configuration and then run it.

#### Running GADGET-2

1.  Navigate to the GADGET-2 test directory:
    ```bash
    cd /workspace/gadget_test
    ```
2.  Modify the `Makefile` and parameter file (`lcdm_gas.param`) for your specific needs.
3.  Execute the run script:
    ```bash
    ./run_gadget.sh
    ```
    This will copy your `Makefile`, recompile GADGET-2, and run it with your parameter file. The output will appear in `/workspace/dockerData` which is mounted from the `dockerData` directory on your host machine.

#### Running GIZMO

1.  Navigate to the GIZMO test directory:
    ```bash
    cd /workspace/gizmo_test
    ```
2.  Modify the `Config.sh` file to enable the physics modules you need.
3.  Modify the `Makefile` if you have special compilation requirements.
4.  Modify the parameter file (`gizmo.param`).
5.  Execute the run script:
    ```bash
    ./run_gizmo.sh
    ```
    This will copy your `Config.sh` and `Makefile`, recompile GIZMO, and run it.

---

## Project Structure

-   `Dockerfile`: Defines the Docker image, installs all dependencies, and copies the source codes.
-   `gadget_test/`: Contains configuration (`Makefile`, `.param`) and the run script (`run_gadget.sh`) for **GADGET-2**.
-   `gizmo_test/`: Contains configuration (`Config.sh`, `Makefile`, `.param`) and the run script (`run_gizmo.sh`) for **GIZMO**.
-   `dockerData/`: A place to store simulation data on your host machine, mounted into the container at `/workspace/dockerData`.

---

## Credits

-   **GADGET-2:** Volker Springel
    -   [https://wwwmpa.mpa-garching.mpg.de/gadget/](https://wwwmpa.mpa-garching.mpg.de/gadget/)
-   **GIZMO:** Philip F. Hopkins
    -   Paper: [Hopkins, P. F. (2015), MNRAS, 450, 53](https://ui.adsabs.harvard.edu/abs/2015MNRAS.450...53H/abstract)
    -   [https://github.com/pfhopkins/gizmo-public](https://github.com/pfhopkins/gizmo-public)
-   Initial Docker setup inspired by Sergey Pilipenko (HSE).

---

## License

For educational and research use only. GADGET-2 and GIZMO are licensed for scientific, non-commercial use.