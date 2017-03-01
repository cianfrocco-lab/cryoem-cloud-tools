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

#This script takes as input a directory containing rosetta score files and outputs a text file with the rosetta pdbs arranged according their energy values.
#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --pdb_list=<.txt file with the list of input pdbs and their weights> --em_map=<EM map in .mrc format> --num=<number of atomic strucutres per CPU process (default:5)")
        parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",
                    help=".txt file with the input pdbs and their weights")
        parser.add_option("--em_map",dest="em_map",type="string",metavar="FILE",
                    help="EM map in .mrc format")
	parser.add_option("--num",dest="num",type="int",metavar="INTEGER",default=5,
                    help="number of structures per CPU (Default = 5)")

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

        if not os.path.exists(params['pdb_list']):
                print "\nError: input pdb list %s doesn't exists, exiting.\n" %(params['pdb_list'])
                sys.exit()
	if not os.path.exists(params['em_map']):
                print "\nError: input EM map list %s doesn't exists, exiting.\n" %(params['em_map'])
                sys.exit()       
#=============================
def makerunfile(params,awsdir):
	#Create output run.sh
	outputrun = 'run_final.sh' 

	#--> Raise error if star file already exists in output location
        if os.path.exists(outputrun):
                print "Error: Output run file %s already exists! Exiting." %(outputrun)
                sys.exit()

	#Open output box file for writing new lines
        outputrun_write = open(outputrun,'w')
	
	#Open the template run.sh file
	inputrun = '%s/rosetta/run_template.sh' %(awsdir)

	#--> Raise error if the templete run.sh file doesnot exist
	if not os.path.exists(inputrun):
        	print "Error: Template run.sh file %s does not exist! Exiting." %(inputrun)
        	sys.exit()
	inputrun_read = open(inputrun, 'r')	
	#Loop over all lines in the input scorefile
        for line in inputrun_read:
		#Split line into values that were separated by tabs
                splitLine = line.split()
		
		if len(line.split()) > 0:
                	if not splitLine[0] == '-mapfile':
				if not splitLine[0] == '-nstruct':
					#Write out the line in the output run file
                        		outputrun_write.write('%s' %(line))
			if splitLine[0] == '-mapfile':
				#Write out the EM map info in the output run file
				map_name = '-mapfile %s \ ' %(params['em_map'])
				outputrun_write.write('    %s\n' %(map_name))
				
			if splitLine[0] == '-nstruct':
				#Write the number of structures to be determined per CPU process
				num_struct = '-nstruct %s \ ' %(params['num'])
				outputrun_write.write('    %s\n' %(num_struct))	
	outputrun_write.close()
	inputrun_read.close()
#========================================
def makeCMfile(params,awsdir):
        #Create output hybrid.xml
        outputhybrid = 'hybridize_final.xml'

        #--> Raise error if star file already exists in output location
        if os.path.exists(outputhybrid):
                print "Error: Output hybrid file %s already exists! Exiting." %(outputhybrid)
                sys.exit()

        #Open output box file for writing new lines
        outputhybrid_write = open(outputhybrid,'w')
        
        #Open the template run.sh file
        inputhybrid = '%s/rosetta/hybridize_template.xml' %(awsdir)

        #--> Raise error if the templete run.sh file doesnot exist
        if not os.path.exists(inputhybrid):
        	print "Error: Template file %s does not exist! Exiting." %(inputhybrid)
        	sys.exit()
        inputhybrid_read = open(inputhybrid, 'r')     
        #Loop over all lines in the input scorefile
        for line in inputhybrid_read:
        	#Split line into values that were separated by tabs
        	splitLine = line.split()
                if len(line.split()) > 0:
			#print line
        		if not splitLine[0] == '<Template':
                        	#Write out the line in the output run file
                        	outputhybrid_write.write('%s' %(line))
                	if splitLine[0] == '<Template':
				pdb_read = open(params['pdb_list'], 'r')
				for pdbline in pdb_read:
					if pdbline[0] == '#':
						continue
					if len(pdbline) == 0: 
						continue
					splitPdb = pdbline.split()
					if len(splitPdb) > 0: 
						newline = '<Template pdb="%s" weight=%s cst_file="AUTO"/>' %(splitPdb[0],splitPdb[1])
						#Write out the line in the output run file
                                		outputhybrid_write.write('            %s\n' %(newline)) 
				pdb_read.close()
	inputhybrid_read.close()
	outputhybrid_write.close()	
#================================================
if __name__ == "__main__":

        params=setupParserOptions()
        awsdir=subprocess.Popen('echo $AWS_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	makerunfile(params,awsdir)
	makeCMfile(params,awsdir)
