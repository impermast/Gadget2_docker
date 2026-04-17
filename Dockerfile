# Dockerfile for GIZMO, GADGET-2 with MPI, FFTW2, GSL 1.16, GalIC, HDF5 and Geany
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NBODY_WORK=/nbody
ENV NBODY_OPT=/opt
ENV HOME=/nbody

# Install system packages and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc gfortran g++ make perl \
    wget curl git ca-certificates \
    openmpi-bin libopenmpi-dev \
    libhdf5-openmpi-dev \
    hdf5-tools \
    libx11-dev libgtk-3-dev hicolor-icon-theme \
    nano vim htop mc geany tmux \
    python3 python3-pip python3-venv python3-lib2to3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create runtime mount point
RUN mkdir -p /nbody

# Build and install GSL 1.16
WORKDIR /opt
RUN wget https://ftp.gnu.org/gnu/gsl/gsl-1.16.tar.gz \
    && tar -xzf gsl-1.16.tar.gz \
    && cd gsl-1.16 \
    && ./configure --prefix=/opt/gsl \
    && make -j$(nproc) && make install \
    && cd .. && rm -rf gsl-1.16 gsl-1.16.tar.gz

# Install FFTW 2.1.5 (MPI, double & single precision)
WORKDIR /opt
RUN wget http://www.fftw.org/fftw-2.1.5.tar.gz \
 && tar -xzf fftw-2.1.5.tar.gz && cd fftw-2.1.5 \
 && ./configure --prefix=/opt/fftw --enable-mpi --enable-shared \
 && make -j$(nproc) && make install && make clean \
 && ./configure --prefix=/opt/fftw --enable-mpi --enable-float --enable-shared \
 && make -j$(nproc) && make install \
 && cd .. && rm -rf fftw-2.1.5 fftw-2.1.5.tar.gz

# --- Download and extract GADGET-2 ---
WORKDIR /opt
RUN wget https://wwwmpa.mpa-garching.mpg.de/gadget/gadget-2.0.7.tar.gz \
    && tar -xzf gadget-2.0.7.tar.gz \
    && rm -f gadget-2.0.7.tar.gz \
    && if [ -d Gadget2 ] && [ ! -d gadget-2.0.7 ]; then mv Gadget2 gadget-2.0.7; fi

# GADGET-2 is not built here. It will be compiled at runtime from /opt/gadget-2.0.7

# --- Install GIZMO ---
WORKDIR /opt
RUN git clone https://github.com/pfhopkins/gizmo-public.git \
    && rm -rf gizmo-public/.git
    
COPY nbody/gizmo_test/GizmoMakefile /opt/gizmo-public/Makefile
COPY nbody/gizmo_test/Makefile.systype /opt/gizmo-public/Makefile.systype

# --- Install snapshot visualizer ---
WORKDIR /opt
RUN git clone https://github.com/spthm/glio \
    && rm -rf glio/.git

WORKDIR /opt/glio
RUN pip3 install --no-cache-dir matplotlib numpy pandas h5py
RUN python3 -m lib2to3 -w .

ENV PYTHONPATH=/opt:/opt/glio:$PYTHONPATH
ENV LD_LIBRARY_PATH=/opt/gsl/lib:/opt/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:$LD_LIBRARY_PATH
ENV GSL_HOME=/opt/gsl
ENV FFTW_HOME=/opt/fftw
ENV GIZMO_HOME=/opt/gizmo-public
ENV GADGET_HOME=/opt/gadget-2.0.7
ENV GLIO_HOME=/opt/glio
ENV GALIC_HOME=/opt/GalIC

# --- Install GalIC ---
WORKDIR /opt
RUN wget https://wwwmpa.mpa-garching.mpg.de/~volker/galic/galic.tar.gz \
    && tar -xzf galic.tar.gz \
    && rm galic.tar.gz \
    && if [ -d /opt/GalIC ]; then echo "GalIC already extracted"; \
       elif [ -d /opt/galic ]; then mv /opt/galic /opt/GalIC; \
       else ls -lah /opt; fi

WORKDIR /opt/GalIC

# Prepare GalIC config files
RUN cp Template-Config.sh Config.sh && \
    cp Template-Makefile.systype Makefile.systype && \
    printf 'SYSTYPE="kds-linux"\n' > Makefile.systype

# Patch GalIC Makefile with local system block if not already present
RUN grep -Fq 'ifeq ($(SYSTYPE),"kds-linux")' Makefile || \
    sed -i '/^ifndef LINKER/i \
ifeq ($(SYSTYPE),"kds-linux")\n\
CC = mpicc\n\
LINKER = $(CC)\n\
OPTIMIZE = -O3 -Wall -Wno-format-security -Wno-unknown-pragmas\n\
\n\
ifeq (NUM_THREADS,$$(findstring NUM_THREADS,$$(CONFIGVARS)))\n\
OPTIMIZE += -fopenmp\n\
endif\n\
\n\
GSL_INCL = -I/opt/gsl/include\n\
GSL_LIBS = -L/opt/gsl/lib\n\
GSLLIB   = -lgsl -lgslcblas\n\
\n\
FFTW_INCL = -I/opt/fftw/include\n\
FFTW_LIB  = -L/opt/fftw/lib -lrfftw_mpi -lfftw_mpi -lrfftw -lfftw\n\
\n\
HDF5INCL = -I/usr/include/hdf5/openmpi -DH5_USE_16_API\n\
HDF5LIB  = -L/usr/lib/x86_64-linux-gnu/hdf5/openmpi -lhdf5 -lz\n\
\n\
MPICHLIB =\n\
GMP_INCL =\n\
GMP_LIBS =\n\
GMPLIB   =\n\
endif\n' Makefile

# Optional: build GalIC during image build
RUN make clean && make -j"$(nproc)"

# Final setup
WORKDIR /nbody
RUN echo "Installation complete. Mount your project directory to /nbody"
ENTRYPOINT ["/bin/bash","-lc"]
CMD ["bash"]
