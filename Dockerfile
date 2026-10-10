# Dockerfile for GIZMO with MPI, FFTW2, GSL 1.16, GalIC, HDF5 and Geany.
# GADGET-2 is available as an optional build component (INSTALL_GADGET=1).
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NBODY_WORK=/nbody
ENV NBODY_OPT=/opt
ENV HOME=/nbody

# Install system packages and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc gfortran g++ make perl \
    wget curl git ca-certificates \
    openmpi-bin libopenmpi-dev \
    libhdf5-openmpi-dev \
    libgmp-dev \
    hdf5-tools \
    libx11-dev libgtk-3-dev hicolor-icon-theme \
    nano vim htop mc geany tmux \
    python3 python3-pip python3-venv python3-lib2to3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create runtime mount point
RUN mkdir -p /nbody

# Build and install GSL 1.16
WORKDIR /opt
RUN wget --timeout=30 --tries=3 https://ftp.gnu.org/gnu/gsl/gsl-1.16.tar.gz \
    && tar -xzf gsl-1.16.tar.gz \
    && cd gsl-1.16 \
    && ./configure --prefix=/opt/gsl \
    && make -j$(nproc) && make install \
    && cd .. && rm -rf gsl-1.16 gsl-1.16.tar.gz

# Install FFTW 2.1.5 (MPI, double & single precision)
WORKDIR /opt
RUN wget --timeout=30 --tries=3 https://www.fftw.org/fftw-2.1.5.tar.gz \
 && tar -xzf fftw-2.1.5.tar.gz && cd fftw-2.1.5 \
 && ./configure --prefix=/opt/fftw --enable-mpi --enable-shared \
 && make -j$(nproc) && make install && make clean \
 && ./configure --prefix=/opt/fftw --enable-mpi --enable-float --enable-shared \
 && make -j$(nproc) && make install \
 && cd .. && rm -rf fftw-2.1.5 fftw-2.1.5.tar.gz

# --- Install a pinned GIZMO source snapshot ---
# This 2021 tree keeps the C layout expected by nbody/gizmo_test/GizmoMakefile.
# The current upstream master has moved to a different C++ layout and is not
# interchangeable with the existing simulation configuration.
WORKDIR /tmp
ARG GIZMO_COMMIT=7182434ce2b0266f2941e28befad3dcdaa914091
ARG GIZMO_SHA256=fc1c98efb8e09d591e36a9c3ceecc5fc6b851382a3ddba36236283ebdc31096c
RUN set -eux; \
    rm -rf /opt/gizmo-public /tmp/gizmo.tar.gz; \
    mkdir -p /opt/gizmo-public; \
    wget -O /tmp/gizmo.tar.gz \
        --timeout=30 --tries=3 \
        "https://github.com/pfhopkins/gizmo-public/archive/${GIZMO_COMMIT}.tar.gz"; \
    echo "${GIZMO_SHA256}  /tmp/gizmo.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/gizmo.tar.gz --strip-components=1 -C /opt/gizmo-public; \
    rm -f /tmp/gizmo.tar.gz

COPY nbody/gizmo_test/GizmoMakefile /opt/gizmo-public/Makefile
COPY nbody/gizmo_test/Makefile.systype /opt/gizmo-public/Makefile.systype

# --- Install snapshot visualizer ---
WORKDIR /opt
RUN git clone --depth 1 https://github.com/spthm/glio \
    && rm -rf glio/.git

WORKDIR /opt/glio
RUN pip3 install --no-cache-dir matplotlib numpy pandas h5py python-telegram-bot
RUN python3 -m lib2to3 -w .

ENV PYTHONPATH=/opt:/opt/glio
ENV LD_LIBRARY_PATH=/opt/gsl/lib:/opt/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi
ENV GSL_HOME=/opt/gsl
ENV FFTW_HOME=/opt/fftw
ENV GSL_DIR=/opt/gsl
ENV FFTW_DIR=/opt/fftw
ENV GIZMO_HOME=/opt/gizmo-public
ENV GADGET_HOME=/opt/gadget-2.0.7
ENV GLIO_HOME=/opt/glio
ENV GALIC_HOME=/opt/GalIC
ENV MPLBACKEND=Agg

# --- Install GalIC ---
# Use a pinned GitHub snapshot because the historical MPA download endpoint is
# unreliable from build hosts and can leave Docker builds waiting indefinitely.
WORKDIR /opt
ARG GALIC_COMMIT=c428d88ec482923e9b0d0e40bae1f5632a810564
ARG GALIC_SHA256=91b91640787236865dd27b30aee9e383a879e9ea46a50f39f4251634d604987a
RUN set -eux; \
    rm -rf /opt/GalIC /tmp/galic.tar.gz; \
    mkdir -p /opt/GalIC; \
    wget -O /tmp/galic.tar.gz \
        --timeout=30 --tries=3 \
        "https://github.com/denisyurin/GALIC/archive/${GALIC_COMMIT}.tar.gz"; \
    echo "${GALIC_SHA256}  /tmp/galic.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/galic.tar.gz --strip-components=1 -C /opt/GalIC; \
    rm -f /tmp/galic.tar.gz

WORKDIR /opt/GalIC

# Prepare GalIC config files and a local system block.
RUN cp Config.sh.template Config.sh && \
    cp Makefile.template Makefile && \
    printf '%s\n' \
        'SYSTYPE="kds-linux"' \
        'CC = mpicc' \
        'CXX = mpicxx' \
        'LINKER = $(CC)' \
        'OPTIMIZE = -O3 -Wall -Wno-format-security -Wno-unknown-pragmas' \
        'GSL_INCL = -I/opt/gsl/include' \
        'GSL_LIBS = -L/opt/gsl/lib' \
        'GSLLIB = -lgsl -lgslcblas' \
        'FFTW_INCL = -I/opt/fftw/include' \
        'FFTW_LIB = -L/opt/fftw/lib -lrfftw_mpi -lfftw_mpi -lrfftw -lfftw' \
        'HDF5INCL = -I/usr/include/hdf5/openmpi -DH5_USE_16_API' \
        'HDF5LIB = -L/usr/lib/x86_64-linux-gnu/hdf5/openmpi -lhdf5 -lz' \
        'MPICHLIB =' \
        'GMP_INCL =' \
        'GMP_LIBS =' \
        'GMPLIB =' \
        > Makefile.systype

# Optional: build GalIC during image build
RUN make clean && make -j"$(nproc)"

# --- Optionally download and extract GADGET-2 ---
# Keep this switch after the common software layers so the large/full variant
# reuses the expensive GIZMO, glio, and GalIC layers from the default build.
# The default image skips this source tree. Build with INSTALL_GADGET=1 when
# GADGET-2 is needed.
WORKDIR /tmp
ARG INSTALL_GADGET=0
ARG GADGET_COMMIT=bddc4a8e90947d62ca8e0b09475b5239ba120d44
ARG GADGET_SHA256=8af9f12ebd3b22e33450f150a73d0706c09bfee03975cabe69284e8c9373a619
RUN set -eux; \
    rm -rf /tmp/gadget-2.0.7-src /opt/gadget-2.0.7; \
    mkdir -p /opt/gadget-2.0.7; \
    if [ "$INSTALL_GADGET" = "1" ]; then \
        mkdir -p /tmp/gadget-2.0.7-src; \
        wget -O /tmp/gadget-2.0.7.tar.gz \
            --timeout=30 --tries=3 \
            "https://github.com/sfebruary/Gadget-2.0.7/archive/${GADGET_COMMIT}.tar.gz"; \
        echo "${GADGET_SHA256}  /tmp/gadget-2.0.7.tar.gz" | sha256sum -c -; \
        tar -xzf /tmp/gadget-2.0.7.tar.gz -C /tmp/gadget-2.0.7-src; \
        gadget_makefile="$(find /tmp/gadget-2.0.7-src -type f -name Makefile -print -quit)"; \
        test -n "$gadget_makefile"; \
        gadget_root="$(dirname "$gadget_makefile")"; \
        cp -a "$gadget_root"/. /opt/gadget-2.0.7/; \
        test -f /opt/gadget-2.0.7/Makefile; \
        rm -rf /tmp/gadget-2.0.7-src /tmp/gadget-2.0.7.tar.gz; \
    else \
        printf '%s\n' 'GADGET-2 is not included in this image. Rebuild with INSTALL_GADGET=1.' \
            > /opt/gadget-2.0.7/README.optional; \
    fi

# GADGET-2 is not built here. It will be compiled at runtime from /opt/gadget-2.0.7

# Final setup
WORKDIR /nbody
RUN echo "Installation complete. Mount your project directory to /nbody"
ENTRYPOINT ["/bin/bash","-lc"]
CMD ["bash"]
