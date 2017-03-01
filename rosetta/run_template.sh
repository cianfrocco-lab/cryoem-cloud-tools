#!/bin/sh
 
/home/Rosetta/3.7_release/main/source/bin/rosetta_scripts.default.linuxgccrelease  \
    -parser:protocol hybridize_final.xml \
    -in:file:fasta cm_full_loops-removed.fasta \
    -relax::cartesian \
    -default_repeats 2 \
    -default_max_cycles 200 \
    -nstruct 5 \
    -mapfile ../../maps/rn15-rd_ct19_locres_filtered.mrc \
    -out::suffix _$1 
