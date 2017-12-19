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

#This script takes as input a list of reference pdb models, the fasta file, cryo EM map and then arranges the inputs for running CM or relax.
#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --pdb_list=<.txt file with the list of input pdbs and their weights> --em_map=<EM map in .mrc format> --fasta=<.fasta file> --num=<number of atomic strucutres per CPU process (default:5) --symm=<symmetry definition file> -r (add this flag if you want to run rosetta relax instead of rosetta CM")
        parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",
                    help=".txt file with the input pdbs and their weights")
        parser.add_option("--em_map",dest="em_map",type="string",metavar="FILE",
                    help="EM map in .mrc format")
	parser.add_option("--fasta",dest="fasta",type="string",metavar="FILE",
                    help=".fasta file for the structure")
	parser.add_option("--num",dest="num",type="int",metavar="INTEGER",default=5,
                    help="number of structures per CPU (Default = 5)")
	parser.add_option("-r", action="store_true",dest="relax",default=False,
                    help="run rosetta relax instead of CM")
	parser.add_option("--symm",dest="symm",type="string",metavar="FILE",
                    help="symmetry definition file")
	parser.add_option("--outdir",dest="outdir",type="string",metavar="FILE",
                    help="Output directory")
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

        if not os.path.exists(params['pdb_list']):
                print "\nError: input pdb list %s doesn't exists, exiting.\n" %(params['pdb_list'])
                sys.exit()
	if not os.path.exists(params['em_map']):
                print "\nError: input EM map list %s doesn't exists, exiting.\n" %(params['em_map'])
                sys.exit()      
	if not params['symm'] == None:
		if not os.path.exists(params['symm']):
			print "\nError: input symmetry definition file %s doesn't exists, exiting.\n" %(params['symm'])
                	sys.exit() 
#=============================
def makerunfile(params):

	#Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        rosettadir='%s/../rosetta/' %(awsdir)

	#Crate output run file
	if params['relax'] == False:
		outputrun = '%s/run_final.sh' %(params['outdir']) 

		#--> Raise error if star file already exists in output location
        	if os.path.exists(outputrun):
                	print "Error: Output run file %s already exists! Exiting." %(outputrun)
                	sys.exit()

		#Open output box file for writing new lines
        	outputrun_write = open(outputrun,'w')
	
		#Open the template run.sh file
		inputrun = '%s/run_cm.sh' %(rosettadir)

		#--> Raise error if the templete run.sh file doesnot exist
		if not os.path.exists(inputrun):
        		print "Error: Template run.sh file %s does not exist! Exiting." %(inputrun)
        		sys.exit()
		inputrun_read = open(inputrun, 'r')	
		#Loop over all lines in the input scorefile
        	for line in inputrun_read:
			#print line
			#Split line into values that were separated by tabs
                	splitLine = line.split()
		
			if len(line.split()) > 0:
				#print splitLine[0]
                		if not splitLine[0] == '-mapfile':
					if not splitLine[0] == '-nstruct':
						if not splitLine[0] == '-in:file:fasta':
							#Write out the line in the output run file
                        				outputrun_write.write('%s' %(line))
				if splitLine[0] == '-mapfile':
					#Write out the EM map info in the output run file
					line_modA = string.replace(line, str(splitLine[1]), str(params['em_map']))
					outputrun_write.write('%s'%(line_modA))	
				if splitLine[0] == '-nstruct':
					#Write the number of structures to be determined per CPU process
					line_modB = string.replace(line, str(splitLine[1]), str(params['num']))
                                	outputrun_write.write('%s'%(line_modB))

				if splitLine[0] == '-in:file:fasta':
                                	#Write the number of structures to be determined per CPU process
					line_modC = string.replace(line, str(splitLine[1]), str(params['fasta']))
                                	outputrun_write.write('%s'%(line_modC))
		outputrun_write.close()
		inputrun_read.close()

	if params['relax'] == True:
                outputrun = '%s/run_final.sh' %(params['outdir'])

                #--> Raise error if star file already exists in output location
                if os.path.exists(outputrun):
                        print "Error: Output run file %s already exists! Exiting." %(outputrun)
                        sys.exit()

                #Open output box file for writing new lines
                outputrun_write = open(outputrun,'w')

                #Open the template run.sh file
                inputrun = '%s/run_relax.sh' %(rosettadir)

                #--> Raise error if the templete run.sh file doesnot exist
                if not os.path.exists(inputrun):
                        print "Error: Template run.sh file %s does not exist! Exiting." %(inputrun)
                        sys.exit()
                inputrun_read = open(inputrun, 'r')
                #Loop over all lines in the input scorefile
                for line in inputrun_read:
                        #print line
                        #Split line into values that were separated by tabs
                        splitLine = line.split()

                        if len(line.split()) > 0:
                                #print splitLine[0]
                                if not splitLine[0] == '-in:file:s':
                                	#Write out the line in the output run file
                                	outputrun_write.write('%s' %(line))
                                if splitLine[0] == '-in:file:s':
					pdb_read = open(params['pdb_list'], 'r')
                                	for pdbline in pdb_read:
                                        	splitPdb = pdbline.split()
                                        	if not splitPdb[0] == '':
							line_modA = string.replace(line, str(splitLine[1]), splitPdb[0])
                                        		outputrun_write.write('%s'%(line_modA))
                outputrun_write.close()
                inputrun_read.close()
#========================================
def makeCMfile(params):
        #Create output hybrid.xml
	#Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        rosettadir='%s/../rosetta/' %(awsdir)

	if params['relax'] == False:
        	outputhybrid = '%s/hybridize_final.xml' %(params['outdir'])

        	#--> Raise error if star file already exists in output location
        	if os.path.exists(outputhybrid):
                	print "Error: Output hybrid file %s already exists! Exiting." %(outputhybrid)
                	sys.exit()

        	#Open output hybrid file for writing new lines
        	outputhybrid_write = open(outputhybrid,'w')
        
        	#Open the template run.sh file
		if params['symm'] == None:
        		inputhybrid = '%s/hybridize.xml' %(rosettadir)
		if not params['symm'] == None:
			inputhybrid = '%s/hybridize_symm.xml' %(rosettadir)
        	#--> Raise error if the templete run.sh file doesnot exist
        	if not os.path.exists(inputhybrid):
        		print "Error: Template file %s does not exist! Exiting." %(inputhybrid)
        		sys.exit()
        	inputhybrid_read = open(inputhybrid, 'r')     
        	#Loop over all lines in the input scorefile
        	for line in inputhybrid_read:
			#print line
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
						splitPdb = pdbline.split()
						if not splitPdb[0] == '':
							replace_name = 'pdb="%s"' %(splitPdb[0])
							replace_weight = 'weight="%s"' %(splitPdb[1])
							weight = float(splitPdb[1])
							#print replace_name
							#print replace_weight
							newline_a = string.replace(line, str(splitLine[1]), str(replace_name))
							newline_b = string.replace(newline_a, str(splitLine[2]), str(replace_weight))
							if not params['symm'] == None:
								#if weight == 0:
									#dummy_str = '%s/>' %('')
									#newline_b = string.replace(newline_b, str(splitLine[-1]), str(dummy_str))
								if weight == 1:
									replace_symm = 'cst_file="AUTO" symmdef="%s"/>' %(params['symm'])
									newline_b = string.replace(newline_b, str(splitLine[-1]), str(replace_symm))
							#newline = '<Template pdb="%s" weight=%s cst_file="AUTO"/>' %(splitPdb[0],splitPdb[1])
							#Write out the line in the output run file
                                			outputhybrid_write.write('%s' %(newline_b)) 
					pdb_read.close()
		inputhybrid_read.close()
		outputhybrid_write.close()

	if params['relax'] == True:
                outputrelax = '%s/relax_final.xml' %(params['outdir'])

                #--> Raise error if star file already exists in output location
                if os.path.exists(outputrelax):
                        print "Error: Output relax file %s already exists! Exiting." %(outputrelax)
                        sys.exit()

                #Open output hybrid file for writing new lines
                outputrelax_write = open(outputrelax,'w')
        
                #Open the template run.sh file
		if params['symm'] == None:
                	inputrelax = '%s/relax.xml' %(rosettadir)
		if not params['symm'] == None:
			inputrelax = '%s/relax_symm.xml' %(rosettadir)
                #--> Raise error if the templete run.sh file doesnot exist
                if not os.path.exists(inputrelax):
                        print "Error: Template file %s does not exist! Exiting." %(inputrelax)
                        sys.exit()
                inputrelax_read = open(inputrelax, 'r')
                #Loop over all lines in the input scorefile
                for line in inputrelax_read:
                        #print line
                        #Split line into values that were separated by tabs
                        splitLine = line.split()
                        if len(line.split()) > 0:
                                #print line
                                if not splitLine[0] == '<LoadDensityMap':
					if not splitLine[0] == '<SetupForSymmetry':
                                        	#Write out the line in the output run file
                                        	outputrelax_write.write('%s' %(line))
                                if splitLine[0] == '<LoadDensityMap':
					replace_name = 'mapfile="%s"/>' %(params['em_map'])
					newline_a = string.replace(line, str(splitLine[2]), str(replace_name))
                                        outputrelax_write.write('%s' %(newline_a))
				if splitLine[0] == '<SetupForSymmetry':
                                        replace_symm = 'definition="%s"/>' %(params['symm'])
                                        newline_a = string.replace(line, str(splitLine[2]), str(replace_symm))
                                        outputrelax_write.write('%s' %(newline_a))
                inputrelax_read.close()
                outputrelax_write.close()	
#================================================
if __name__ == "__main__":

        params=setupParserOptions()
	checkConflicts(params)
        makerunfile(params)
	makeCMfile(params)
