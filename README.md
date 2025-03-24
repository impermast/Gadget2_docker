# GADGET-2 Docker Environment

This repository contains a Docker environment for building and running **GADGET-2**, a cosmological N-body/SPH simulation code. It includes all necessary dependencies, including:

- **MPI** (OpenMPI)
- **HDF5** with MPI support
- **FFTW 2.1.5** (compiled from source)
- **GSL 1.16** (compiled from source)
- **Geany** editor and other common CLI tools

## 🧱 What's inside

- `Dockerfile`: Installs dependencies, compiles GSL, FFTW2, GADGET-2
- `Makefile.systype`: Configuration for building GADGET-2 with MPI, FFTW2, and GSL
- `parameterfiles/`: Includes a working `example.param` file and `outputs_lcdm_gas.txt`
- `ICs/`: Includes initial conditions (example: `lcdm_gas_littleendian.dat`)
- `run_test/run_gadget.sh`: Script to launch a sample simulation

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
docker run -it --rm -v $(pwd)/output:/workspace/run_test/output gadget2
```

### 3. Run the test simulation

Inside the container:

```bash
./run_gadget.sh
```

Output will be written to `/workspace/run_test/output`.

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

---

## 📎 Credits

- GADGET-2 by Volker Springel: [wwwmpa.mpa-garching.mpg.de/gadget](https://wwwmpa.mpa-garching.mpg.de/gadget/)
- Installation guide partially inspired by lecture materials by Sergey Pilipenko (HSE)

---

## 📬 License

This project is open for educational and research purposes. GADGET-2 itself is licensed for scientific, non-commercial use.

