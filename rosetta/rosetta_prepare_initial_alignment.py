#!/usr/bin/env python
from operator import itemgetter
import shutil
import optparse
from sys import *
import os,sys,re
from optparse import OptionParser
import glob
import subprocess
from os import system
import linecache
import time
import string

#This script takes as input a .hhr list, calls prepare_hybridize_from_hhsearch.pl to generate the alignments.filt file (alignment in rosetta format) then uses the alignment.flt, fasta file and reference pdb (from rcsb pdb) to gerate partially threaded template.
#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --align_list=<.hhr file with the list of alignments to available structures generated using HHpred> --fasta=<.fasta file>")
        parser.add_option("--align_list",dest="align_list",type="string",metavar="FILE",
                    help=".hhr file with the alignments")
	parser.add_option("--fasta",dest="fasta",type="string",metavar="FILE",
                    help="fasta file")

	options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) <= 2:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#=============================
def checkConflicts(params):

        if not os.path.exists(params['align_list']):
                print "\nError: input alignment list %s doesn't exists, exiting.\n" %(params['align_list'])
                sys.exit()
	if not os.path.exists(params['fasta']):
                print "\nError: input fasta file %s doesn't exists, exiting.\n" %(params['fasta'])
                sys.exit()       
#=============================
def makethreadfile(params):

	#Crate output run file
	outputthread = 'thread_final.sh' 

	#--> Raise error if star file already exists in output location
        if os.path.exists(outputthread):
                print "Error: Output thread file %s already exists! Exiting." %(outputthread)
                sys.exit()

	#Open output thread file for writing new lines
        outputthread_write = open(outputthread,'w')
	
	#Open the template thread.sh file
	inputthread = 'thread.sh'

	#--> Raise error if the templete thread.sh file doesnot exist
	if not os.path.exists(inputthread):
        	print "Error: Template thread.sh file %s does not exist! Exiting." %(inputthread)
        	sys.exit()
	inputthread_read = open(inputthread, 'r')	
	#Loop over all lines in the input thread file
        for line in inputthread_read:
		#Split line into values that were separated by tabs
                splitLine = line.split()
		
		if len(line.split()) > 0:
                	if not splitLine[0] == './prepare_hybridize_from_hhsearch.pl':
				if not splitLine[0] == '/home/Rosetta/2017_08/main/source/bin/partial_thread.static.linuxgccrelease':
					#Write out the line in the output run file
                        		outputthread_write.write('%s' %(line))
			if splitLine[0] == './prepare_hybridize_from_hhsearch.pl':
				line_modA = string.replace(line, str(splitLine[1]), str(params['align_list']))
				outputthread_write.write('%s'%(line_modA))	
			if splitLine[0] == '/home/Rosetta/2017_08/main/source/bin/partial_thread.static.linuxgccrelease':
				line_modB = string.replace(line, str(splitLine[2]), str(params['fasta']))
                                outputthread_write.write('%s'%(line_modB))

	outputthread_write.close()
	inputthread_read.close()
	cmd = '/bin/chmod 765 thread_final.sh'
	subprocess.Popen(cmd,shell=True).wait()
	print cmd
	cmd = './thread_final.sh'
        subprocess.Popen(cmd,shell=True).wait()
	print cmd
#========================================
#================================================
if __name__ == "__main__":

        params=setupParserOptions()
        makethreadfile(params)

	print 'rosetta_finished'
