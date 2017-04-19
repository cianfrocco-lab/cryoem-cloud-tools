#!/bin/sh
 
/home/Rosetta/2017_08/main/source/bin/rosetta_scripts.static.linuxgccrelease  \
    -parser:protocol hybridize_final.xml \
    -in:file:fasta fasta.fasta \
    -relax::cartesian \
    -default_repeats 2 \
    -default_max_cycles 200 \
    -nstruct 1 \
    -mapfile mapfile.mrc \
    -out::suffix _$1 
