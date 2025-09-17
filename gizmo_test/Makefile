# GIZMO Makefile for Docker Environment

#----------------------------------------------------------------------
#       Compiler and Flags
#----------------------------------------------------------------------

CC = mpicc
CXX = mpicxx
OPTIMIZE = -O3 -Wall
CFLAGS = $(OPTIMIZE)

#----------------------------------------------------------------------
#       Library Paths (configured for this Docker image)
#----------------------------------------------------------------------

# GSL (GNU Scientific Library)
GSL_DIR ?= /workspace/gsl
GSL_INCL = -I$(GSL_DIR)/include
GSL_LIBS = -L$(GSL_DIR)/lib -lgsl -lgslcblas

# FFTW (Fastest Fourier Transform in the West)
FFTW_DIR ?= /workspace/fftw
FFTW_INCL = -I$(FFTW_DIR)/include
FFTW_LIBS = -L$(FFTW_DIR)/lib -lrfftw_mpi -lfftw_mpi -lrfftw -lfftw

# HDF5 (Hierarchical Data Format 5)
# These are in standard system paths, so the compiler should find them
HDF5_INCL = -I/usr/include/hdf5/openmpi
HDF5_LIBS = -L/usr/lib/x86_64-linux-gnu/hdf5/openmpi -lhdf5 -lz

# MPI (Message Passing Interface)
MPI_INCL =
MPI_LIBS =

#----------------------------------------------------------------------
#       Combine flags and libraries
#----------------------------------------------------------------------

INCL = $(GSL_INCL) $(FFTW_INCL) $(HDF5_INCL) $(MPI_INCL)
LIBS = $(GSL_LIBS) $(FFTW_LIBS) $(HDF5_LIBS) $(MPI_LIBS) -lm

#----------------------------------------------------------------------
#       Executable and Object files
#----------------------------------------------------------------------

EXEC = GIZMO
OBJS = # This will be populated by the GIZMO make system

# Default target
all: $(EXEC)

$(EXEC):
	@echo "Running GIZMO main makefile..."
	$(MAKE) -f Makefile.gizmo CFLAGS_EXTRA="$(CFLAGS) $(INCL)" LIBS_EXTRA="$(LIBS)"

clean:
	rm -f $(EXEC) *.o

# This is a wrapper Makefile. The actual build is handled by Makefile.gizmo
# which is part of the GIZMO source. We pass our library paths to it.
