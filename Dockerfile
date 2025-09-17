# Dockerfile for GADGET-2 with MPI, FFTW2, GSL 1.16, HDF5 and Geany
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME /workspace

# Install system packages and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc gfortran g++ make \
    wget curl git \
    openmpi-bin libopenmpi-dev \
    libhdf5-openmpi-dev \
    hdf5-tools \
    libx11-dev libgtk-3-dev \
    nano vim htop mc geany \
    python3 python3-pip python3-venv \
    && apt-get clean

# Build and install GSL 1.16
WORKDIR /workspace
RUN wget https://ftp.gnu.org/gnu/gsl/gsl-1.16.tar.gz \
    && tar -xzf gsl-1.16.tar.gz \
    && cd gsl-1.16 \
    && ./configure --prefix=/workspace/gsl \
    && make -j$(nproc) && make install \
    && cd .. && rm -rf gsl-1.16*

RUN wget http://www.fftw.org/fftw-2.1.5.tar.gz \
    && tar -xzf fftw-2.1.5.tar.gz \
    && cd fftw-2.1.5 \
    && ./configure --prefix=/workspace/fftw --enable-mpi \
    && make -j$(nproc) && make install \
    && cd .. && rm -rf fftw-2.1.5*

# Download and extract GADGET-2
RUN wget https://wwwmpa.mpa-garching.mpg.de/gadget/gadget-2.0.7.tar.gz \
    && tar -xzf gadget-2.0.7.tar.gz  && \
    rm -rf gadget-2.0.7.tar.gz

# GADGET-2 is not built here. It will be compiled at runtime using the run_gadget.sh script.

# --- Install GIZMO ---
WORKDIR /workspace
RUN git clone https://github.com/pfhopkins/gizmo-public.git


#Downloading snapshot visual
WORKDIR /workspace
RUN git clone https://github.com/spthm/glio
WORKDIR /workspace/glio
RUN pip install 2to3 matplotlib numpy pandas
RUN 2to3 -w ./ 
ENV PYTHONPATH=/workspace:$PYTHONPATH

# Copy GIZMO test configuration and run script
COPY gizmo_test /workspace/gizmo_test
RUN chmod +x /workspace/gizmo_test/run_gizmo.sh

# Copy GADGET test configuration and run script
COPY gadget_test /workspace/gadget_test
RUN chmod +x /workspace/gadget_test/run_gadget.sh

# Final setup
WORKDIR /workspace
RUN echo "Installation complete. You can now run simulations using the scripts in /workspace/gadget_test or /workspace/gizmo_test"
ENTRYPOINT ["/bin/bash","-lc"]
CMD ["bash"]
