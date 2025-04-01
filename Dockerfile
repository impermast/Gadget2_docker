# Dockerfile for GADGET-2 with MPI, FFTW2, GSL 1.16 and Geany (no HDF5)
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system packages and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc gfortran g++ make \
    wget curl git \
    openmpi-bin libopenmpi-dev \
    libx11-dev libgtk-3-dev \
    nano vim htop mc geany \
    python3 python3-pip python3-venv\
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

# Copy your custom Makefile (from root dir)
COPY Makefile /workspace/Gadget-2.0.7/Gadget2/Makefile

# Build GADGET-2
WORKDIR /workspace/Gadget-2.0.7/Gadget2
RUN make clean && make

#Downloading snapshot visual
WORKDIR /workspace
RUN git clone https://github.com/spthm/glio
WORKDIR /workspace/glio
RUN pip install 2to3
RUN 2to3 -w ./

#TestRun
WORKDIR /workspace
COPY run_test /workspace/run_test
RUN echo -e "\nInstallation completed\n\n Execute ./run_gadget"
CMD ["bash"]
