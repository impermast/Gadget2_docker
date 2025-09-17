# Simple Makefile for GADGET-2 (no HDF5)

# ---- Compile-time options (enable/disable as needed)
OPT  += -DPERIODIC
OPT  += -DUNEQUALSOFTENINGS
OPT  += -DPEANOHILBERT
OPT  += -DWALLCLOCK
OPT  += -DPMGRID=128
#OPT += -DDOUBLEPRECISION
#OPT += -DDOUBLEPRECISION_FFTW
OPT  += -DSYNCHRONIZATION
# No HDF5:
#OPT += -DHAVE_HDF5
OPT  += -DNOTYPEPREFIX_FFTW

# ---- Toolchain & flags
CC        := mpicc
OPTIMIZE  := -O3 -Wall
CSTD      := -std=gnu99
OPTIONS   := $(OPTIMIZE) $(CSTD) $(OPT)

# ---- Paths (override via env if needed)
GSL_DIR   ?= /workspace/gsl
FFTW_DIR  ?= /workspace/fftw

GSL_INCL  := -I$(GSL_DIR)/include
GSL_LIBS  := -L$(GSL_DIR)/lib

FFTW_INCL := -I$(FFTW_DIR)/include
FFTW_LIBS := -L$(FFTW_DIR)/lib

# ---- FFTW linking (depends on precision/options)
ifeq (NOTYPEPREFIX_FFTW,$(findstring NOTYPEPREFIX_FFTW,$(OPT)))
  FFTW_LIB := $(FFTW_LIBS) -lrfftw_mpi -lfftw_mpi -lrfftw -lfftw
else
  ifeq (DOUBLEPRECISION_FFTW,$(findstring DOUBLEPRECISION_FFTW,$(OPT)))
    FFTW_LIB := $(FFTW_LIBS) -ldrfftw_mpi -ldfftw_mpi -ldrfftw -ldfftw
  else
    FFTW_LIB := $(FFTW_LIBS) -lsrfftw_mpi -lsfftw_mpi -lsrfftw -lsfftw
  endif
endif

# ---- Final flags
CFLAGS := $(OPTIONS) $(GSL_INCL) $(FFTW_INCL)
LIBS   := $(GSL_LIBS) -lgsl -lgslcblas -lm $(FFTW_LIB)

# ---- Targets
EXEC := Gadget2
OBJS := main.o run.o predict.o begrun.o endrun.o global.o timestep.o \
        init.o restart.o io.o accel.o read_ic.o ngb.o system.o allocate.o \
        density.o gravtree.o hydra.o driftfac.o domain.o allvars.o \
        potential.o forcetree.o peano.o gravtree_forcetest.o \
        pm_periodic.o pm_nonperiodic.o longrange.o

INCL := allvars.h proto.h tags.h Makefile

all: $(EXEC)

$(EXEC): $(OBJS)
	$(CC) $(OBJS) $(LIBS) -o $@

%.o: %.c $(INCL)
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(EXEC)

.PHONY: all clean
