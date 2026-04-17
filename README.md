# Dockerized GADGET-2 / GIZMO Environment

This repository provides a Docker-based environment for building and running cosmological N-body/SPH simulations with **GADGET-2**, **GIZMO**, and **GalIC**.

The main goal of this setup is to remove the need for manual system preparation on each machine. After a single Docker build, all required dependencies, compiler toolchains, libraries, helper Python packages, and bundled third-party source trees are installed automatically inside the image.

In practice, this means that you do not need to manually install or configure MPI, GSL, FFTW, HDF5, Python modules, or patch build environments separately on every target server. The Docker image already prepares the required software stack and internal paths during the build process.

The image also provides a ready-to-use build environment for the simulation codes. In particular, bundled components such as **GalIC** are configured automatically during image build, including preparation of the corresponding build files. This significantly reduces the amount of manual setup usually required when deploying the same workflow on a new machine.

The project uses the following layout inside the container:

- **`/opt`** — stable software layer containing installed dependencies and bundled third-party source trees
- **`/nbody`** — user workspace mounted from the host machine

This approach allows you to keep all heavy and rarely changing software inside the image, while editing your own simulation scripts, parameter files, and test setups locally without rebuilding the container.

Once the image has been built, the environment can be deployed on any compatible server with Docker using the same command:

```bash
docker build -t gadget-gizmo:ver2 .
```

After that, the container already contains the required scientific software stack and is ready for runtime compilation and execution of your local GADGET-2 / GIZMO workflows.
---

## Features

- **Reproducible environment** based on Ubuntu 20.04.
- Preinstalled scientific stack:
  - OpenMPI
  - GSL 1.16
  - FFTW 2.1.5
  - HDF5
  - Python 3 with helper libraries
- Included third-party source trees inside the image:
  - **GADGET-2**
  - **GIZMO**
  - **GalIC**
  - **glio**
- **Runtime compilation workflow**:
  build and run simulation codes from wrapper scripts in your mounted workspace.
- **Clean separation of concerns**:
  local project files live in `nbody/`, system dependencies live in `/opt`.

---

### Directory roles

* **`Dockerfile`**
  Builds the image and installs all system dependencies and third-party codes into `/opt`.

* **`run_docker_gui_linux.sh`**
  Starts the container, mounts local `nbody/` into `/nbody`, and enables X11 GUI applications.

* **`nbody/`**
  Main user workspace on the host machine.
  Everything in this directory becomes available inside the container at:

---
## Repository Layout

```text
.
├── Dockerfile
├── README.md
├── run_docker_gui_linux.sh
└── nbody/
    ├── gadget_test/
    ├── gizmo_test/
    ├── GalIC/
    ├── scripts/
    ├── testGraphs/
    └── ...
```

## Container Layout

Inside the container, the structure is:

```text
/opt
├── gsl
├── fftw
├── glio
├── gadget-2.0.7
├── gizmo-public
└── GalIC

/nbody
└── ...   ← mounted from host ./nbody
```

## How to Build the Image

From the root of the repository, run:

```bash
docker build -t gadget-gizmo:ver2 .
```

This builds the full environment and stores all dependencies and third-party source trees inside the image.

---

## How to Start the Container

Run:

```bash
./run_docker_gui_linux.sh
```

The script will:

* ensure Docker daemon is running,
* enable X11 forwarding for GUI tools,
* mount local `./nbody` into container `/nbody`,
* start or recreate the container if needed.

By default, the script uses the image:

```bash
gadget-gizmo:ver2
```

---

## Workflow

The intended workflow is:

1. Build the image once.
2. Edit your configs, parameter files, and helper scripts locally in `nbody/`.
3. Start the container.
4. Run wrapper scripts from `/nbody/...`.
5. Keep outputs in `/nbody/...` so they remain on the host system.
6. commit new created features from your local machine.

---

## Running GADGET-2

Inside the container:

```bash
cd /nbody/gadget_test
./run_gadget.sh
```

Typical logic of the wrapper script:

* use your local configuration files from `/nbody/gadget_test`,
* compile **GADGET-2** against the source tree in `/opt/gadget-2.0.7`,
* execute the simulation,
* write outputs into directories under `/nbody`.

You should edit your parameter files and build configuration in:

```bash
/nbody/gadget_test
```

not inside `/opt`.

---

## Running GIZMO

Inside the container:

```bash
cd /nbody/gizmo_test
./run_gizmo.sh
```

Typical logic of the wrapper script:

* use your local `Config.sh`, `Makefile`, and parameter files from `/nbody/gizmo_test`,
* compile **GIZMO** against `/opt/gizmo-public`,
* run the selected setup,
* store outputs under `/nbody`.

All user changes should stay inside:

```bash
/nbody/gizmo_test
```

---

## Using GalIC

**GalIC** is installed inside the image at:

```bash
/opt/GalIC
```

Recommended workflow:

* keep the **GalIC binary and source tree** in `/opt/GalIC`,
* keep your **parameter files, generated models, and outputs** in `/nbody/GalIC`.

Example:

```bash
cd /opt/GalIC
./GalIC /nbody/GalIC/params/your_model.param
```

This keeps the source tree stable while preserving all your inputs and outputs on the host.

---

## Notes on Editing Files

### Edit here

These are the directories you are expected to modify:

```bash
/nbody/gadget_test
/nbody/gizmo_test
/nbody/GalIC
/nbody/scripts
```

### Do not edit here unless you really intend to modify bundled source code

These directories belong to the Docker image:

```bash
/opt/gadget-2.0.7
/opt/gizmo-public
/opt/GalIC
/opt/glio
/opt/gsl
/opt/fftw
```

If you need to change bundled source code in `/opt`, the proper way is usually to modify the Dockerfile and rebuild the image.

---

## Credits

* **GADGET-2** — Volker Springel
* **GIZMO** — Philip F. Hopkins
* **GalIC** — Volker Springel
* **glio** — snapshot visualization helper library

Any questions can be adressed to Dmitry Kalashnikov dskalashnikov@mephi.ru

---

## License

This repository is intended for educational and research use.

Please check the original licenses and usage restrictions of:

* GADGET-2
* GIZMO
* GalIC
* glio

These third-party packages remain subject to their own licensing terms.

