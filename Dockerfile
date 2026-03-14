# Dockerfile for GIZMO, GADGET-2 with MPI, FFTW2, GSL 1.16, GalIC, HDF5 and Geany
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME /workspace

# Install system packages and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc gfortran g++ make perl \
    wget curl git ca-certificates \
    openmpi-bin libopenmpi-dev \
    libhdf5-openmpi-dev \
    hdf5-tools \
    libx11-dev libgtk-3-dev hicolor-icon-theme \
    nano vim htop mc geany \
    python3 python3-pip python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Build and install GSL 1.16
WORKDIR /workspace
RUN wget https://ftp.gnu.org/gnu/gsl/gsl-1.16.tar.gz \
    && tar -xzf gsl-1.16.tar.gz \
    && cd gsl-1.16 \
    && ./configure --prefix=/workspace/gsl \
    && make -j$(nproc) && make install \
    && cd .. && rm -rf gsl-1.16*

# Установка FFTW 2.1.5 (MPI, double & single precision)
RUN wget http://www.fftw.org/fftw-2.1.5.tar.gz \
 && tar -xzf fftw-2.1.5.tar.gz && cd fftw-2.1.5 \
 && ./configure --prefix=/workspace/fftw --enable-mpi --enable-type-prefix --enable-shared \
 && make -j$(nproc) && make install && make clean \
 && ./configure --prefix=/workspace/fftw --enable-mpi --enable-float --enable-type-prefix --enable-shared \
 && make -j$(nproc) && make install \
 && cd .. && rm -rf fftw-2.1.5*




#  --- Download and extract GADGET-2 ---
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
RUN pip install --no-cache-dir 2to3 matplotlib numpy pandas h5py
RUN 2to3 -w ./ 

ENV PYTHONPATH=/workspace:/workspace/glio:$PYTHONPATH
ENV LD_LIBRARY_PATH=/workspace/gsl/lib:/workspace/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:$LD_LIBRARY_PATH


# --- Install GalIC ---
WORKDIR /workspace
RUN wget https://wwwmpa.mpa-garching.mpg.de/~volker/galic/galic.tar.gz && \
    tar -xzf galic.tar.gz && \
    rm galic.tar.gz

# normalize extracted directory name if needed
RUN if [ -d /workspace/GalIC ]; then echo "GalIC already extracted"; \
    elif [ -d /workspace/galic ]; then mv /workspace/galic /workspace/GalIC; \
    else ls -lah /workspace; fi
WORKDIR /workspace/GalIC

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
GSL_INCL = -I/workspace/gsl/include\n\
GSL_LIBS = -L/workspace/gsl/lib\n\
GSLLIB   = -lgsl -lgslcblas\n\
\n\
FFTW_INCL = -I/workspace/fftw/include\n\
FFTW_LIB  = -L/workspace/fftw/lib -lrfftw_mpi -lfftw_mpi -lrfftw -lfftw\n\
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




# Copy GIZMO test configuration and run script
WORKDIR /workspace
COPY gizmo_test /workspace/gizmo_test
RUN chmod +x /workspace/gizmo_test/run_gizmo.sh
#
COPY gizmo_test/Config_cdm_sidm.sh /workspace/gizmo_test/
COPY gizmo_test/gizmo_sidm.param   /workspace/gizmo_test/
COPY gizmo_test/gizmo_cdm.param    /workspace/gizmo_test/
COPY scripts/analyze_halo.py       /workspace/scripts/
COPY scripts/convert_to_pt3.py     /workspace/scripts/
COPY GalIC/Model_H1_light.param    /workspace/GalIC/

# Copy GADGET test configuration and run script
COPY gadget_test /workspace/gadget_test
RUN chmod +x /workspace/gadget_test/run_gadget.sh

# Final setup
WORKDIR /workspace
RUN echo "Installation complete. You can now run simulations using the scripts in /workspace/gadget_test or /workspace/gizmo_test"
ENTRYPOINT ["/bin/bash","-lc"]
CMD ["bash"]
