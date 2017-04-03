#!/bin/sh
 
/home/Rosetta/2017_08/main/source/bin/rosetta_scripts.static.linuxgccrelease  \
    -parser:protocol hybridize_final.xml \
    -in:file:fasta cm_full_loops-removed.fasta \
    -relax::cartesian \
    -default_repeats 2 \
    -default_max_cycles 200 \
    -nstruct 5 \
    -mapfile ../../maps/rn15-rd_ct19_locres_filtered.mrc \
    -out::suffix _$1 
