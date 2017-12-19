#!/usr/bin/env python
from operator import itemgetter
import shutil
import optparse
from sys import *
import os,sys,re
import argparse
import glob
import subprocess
from os import system
import linecache
import time
import string

#This script takes as input a .pdb file, symmetrize it and generate the symmetry definition file. Currently we support only NCS  
#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --pdb=<pdb file with all the chains roughly fitted in the EM map> --main=<main chain> --symm=<symmetry related chains; enclose within quotes> --output=<name of the output symmetry definition file> ")
        parser.add_option("--pdb",dest="pdb",type="string",metavar="FILE",
                    help="pdb model with all the chains")
	parser.add_option("--main",dest="main",type="string",metavar="FILE",
                    help="main chain of the pdb file")
	parser.add_option("--symm",dest="symm",type="string",metavar="FILE",
                    help="symmetry related chains; enclose within quotes; if there aremultiple such chains then separate them with space")
	parser.add_option("--output",dest="output",type="string",metavar="FILE",
                    help="name of the output symmetry definition file; don't include any extension")
	parser.add_option("--distance",dest="distance",type="int",metavar="INTEGER",default=1000,
                    help="-r option of rosetta symmetry file generation. Default:1000")

	options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) <= 3:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#=============================
def checkConflicts(params):

        if not os.path.exists(params['pdb']):
                print "\nError: input pdb file %s doesn't exists, exiting.\n" %(params['pdb'])
                sys.exit()
#	if os.path.exists(params['output']):
#                print "\nError: output symmetry definition file %s already exists, exiting.\n" %(params['output'])
#                sys.exit()       
#=============================
def makesymmfile(params):

	#Crate final symmetry file
        outputthread = '%s.symm' %(params['output'])

	#Create temporary symmetry file
        inputthread = 'symmetry.symm'

        #--> Raise error if star file already exists in output location
        if os.path.exists(outputthread):
                print "Error: Final symmetry definition file %s already exists! Exiting." %(outputthread)
                sys.exit()

	if os.path.exists(inputthread):
                print "Error: Temporary symmetry definition file %s already exists! Exiting." %(inputthread)
                sys.exit()

        #Open output thread file for writing new lines
        outputthread_write = open(outputthread,'w')

	cmd = '/home/Rosetta/2017_08/main/source/src/apps/public/symmetry/make_symmdef_file.pl \ -m NCS -a %s -i %s \ -p %s -r %i > symmetry.symm' %(params['main'],params['symm'], params['pdb'], params['distance'])
        subprocess.Popen(cmd,shell=True).wait()
	print cmd 

	#Open the symmetry definition file
	#inputthread = 'symmetry.symm'

	#--> Raise error if the templete thread.sh file doesnot exist
	if not os.path.exists(inputthread):
        	print "Error: Symmetry definition file %s does not exist! Exiting." %(inputthread)
        	sys.exit()
	inputthread_read = open(inputthread, 'r')
	counter = 0	
	#Loop over all lines in the input thread file
        for line in inputthread_read:
		#Split line into values that were separated by tabs
                splitLine = line.split()
		if len(line.split()) > 0:
                	if splitLine[0] == 'set_dof':
				if not counter == 0:
					outputthread_write.write('%s'%(line))
				if counter == 0:
					line_modA = 'set_dof JUMP0_0_to_com x y z\n'
					outputthread_write.write('%s' %(line_modA))	
					counter = counter + 1
			if not splitLine[0] == 'set_dof':
				#line_modB = string.replace(line, str(splitLine[2]), str(params['fasta']))
                                outputthread_write.write('%s'%(line))
	outputthread_write.close()
	inputthread_read.close()
	cmd = 'rm -rf symmetry.symm'
        subprocess.Popen(cmd,shell=True).wait()
	print cmd
#========================================
#================================================
if __name__ == "__main__":

        params=setupParserOptions()
        makesymmfile(params)

