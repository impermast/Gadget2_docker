# GADGET-2 Docker Environment

This repository contains a Docker environment for building and running **GADGET-2**, a cosmological N-body/SPH simulation code. It includes all necessary dependencies, including:

* **MPI** (OpenMPI)
* **FFTW 2.1.5** (compiled from source)
* **GSL 1.16** (compiled from source)
* **Geany** editor and other common CLI tools

## 🧱 What's inside

* `Dockerfile`: Installs dependencies, compiles GSL, FFTW2, GADGET-2
* `Makefile`: Configuration for building GADGET-2 with MPI, FFTW2, and GSL
* `run_test/run_gadget.sh`: Script to launch a sample simulation

---

## 🚀 Quick Start

### 1. Clone and build the image

```bash
git clone https://github.com/impermast/gadget2-docker.git
cd gadget2-docker
docker build -t gadget2 .
```

### 2. Run the container

```bash
docker run -it gadget2
```

or if you work in linux and want gui

```bash
chmod +x run_gadget_gui_linux.sh
./run_gadget_gui_linux.sh
```

### 3. Run the test simulation

Inside the container:

```bash
./run_gadget.sh
```

Output will be written to `/workspace/dockerData`.

### 4. `dockerData/` directory

To exchange files (e.g. input data, output snapshots, logs) between the Docker container and the host system, use the mounted directory:

`/workspace/dockerData`

This directory is accessible both inside and outside the container, and is ideal for persistent storage and communication with your host environment. You can mount this folder when starting the container with:

```bash
docker run -it -v $(pwd)/dockerData:/workspace/dockerData gadget2
```

Make sure `/dockerData`  exists on the host side before running.

---

## 🛠 File descriptions

### `example.param`

Parameter file controlling the simulation. Includes paths to ICs and output directory.

### `outputs_lcdm_gas.txt`

List of scale factors at which snapshots will be written.

### `run_gadget.sh`

Simple wrapper to call GADGET-2 with MPI:

```bash
mpirun -n 1 /opt/Gadget-2.0.7/Gadget2/Gadget2 /workspace/parameterfiles/example.param
```

This script also automatically:

* Copies the selected Makefile and parameter file into the GADGET source directory
* Rebuilds the code with `make`
* Copies the executable back and runs it with the given parameter file
* **Creates the output directory if it doesn't exist** (based on `OutputDir` from the `.param` file)

---

## 📌 Modeling notes

### Makefile

The project uses a clean Makefile with:

* `mpicc` as compiler
* GSL and FFTW paths fixed to `/workspace/gsl` and `/workspace/fftw`
* `OPT = NOTYPEPREFIX_FFTW` (used by default)

Only physics modeling parameters should be defined in `.param` files.

### Parameter file (`.param`)

For every simulation, make sure to:

* Provide a correct `InitCondFile`, e.g.:

  ```
  InitCondFile lcdm_gas_littleendian.dat
  ```
* Set an `OutputDir`, e.g.:

  ```
  OutputDir /workspace/run_test/galaxy
  ```

> **Note:** GADGET-2 does *not* create the output directory automatically. If it does not exist, the simulation will crash. The `run_gadget.sh` script takes care of this automatically by parsing `OutputDir` and creating the directory before launch.

---

## 📌 Credits

* GADGET-2 by Volker Springel: [wwwmpa.mpa-garching.mpg.de/gadget](https://wwwmpa.mpa-garching.mpg.de/gadget/)
* Installation guide partially inspired by lecture materials by Sergey Pilipenko (HSE)

---

## 📬 License

This project is open for educational and research purposes. GADGET-2 itself is licensed for scientific, non-commercial use.
