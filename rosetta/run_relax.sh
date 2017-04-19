#!/bin/sh

/home/Rosetta/2017_08/main/source/bin/rosetta_scripts.static.linuxgccrelease  \
	-parser:protocol relax_final.xml \
	-in:file:s pdbfile.pdb \
	-default_max_cycles 200 \
	-nstruct 1 \
    -cryst::crystal_refine \
	-out::suffix _$1
