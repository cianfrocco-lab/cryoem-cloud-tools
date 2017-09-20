#!/bin/sh

./prepare_hybridize_from_hhsearch.pl Rpb*.hhr
/home/Rosetta/2017_08/main/source/bin/partial_thread.static.linuxgccrelease -in::file::fasta Rpb*.fasta -in::file::alignment alignments.filt -in::file::template_pdb ?????.pdb
