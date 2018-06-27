#!/usr/bin/env python
import pickle
import datetime 
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
from fabric.operations import run, put
from fabric.api import env,run,hide,settings
from fabric.context_managers import shell_env

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.add_option("--em_map",dest="em_map",type="string",metavar="FILE",
                    help="EM map in .mrc format")
	parser.add_option("--fasta",dest="fasta",type="string",metavar="FILE",
                    help="FASTA sequence file (not required for rosetta relax)")
	parser.add_option("--hhr",dest="hhr",type="string",metavar="FILE",default='',
                    help=".hhr sequence alignment file")
	parser.add_option("-r", action="store_true",dest="relax",default=False,
                    help="run rosetta relax instead of CM")
	parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",default='',
                    help="PDB reference file OR .txt file with the input pdbs and their weights. List is required Only required if no .hhr file provided")
	parser.add_option("--num",dest="num_models",type="int",metavar="INT",default=216,
                    help="Total number of structures to calculate. (Default = 216)")
	parser.add_option("--numCPU",dest="num_models_per_instance",type="int",metavar="INT",default=36,
                    help="Number of CPUs to use. (Default = 36)")
	parser.add_option("--sym",dest="sym",type="string",metavar="string",default='C1',
                    help="Symmetry of map (Default = C1) or path to Rosetta symmetry file")
	parser.add_option("--outdir",dest="outdir",type="string",metavar="DIR",default='',
		    help="Optional: Name of output directory. Otherwise, output directory will be automatically generated")
	parser.add_option("--nocheck", action="store_true",dest="nocheck",default=False,
                    help="Include this option to not stop after preparing PDB files, instead continuing straight into Rosetta-CM")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
            help="debug")	
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
def checkConflicts(params,outdir):

	#Check rosettadir path
	#check for parallel to be installed

	if params['relax'] is True: 
		if len(open(params['pdb_list'],'r').readlines()) > 1: 
			print '\nError: Rosetta-Relax will only operate on a single PDB file. Exiting.'
			sys.exit()
	
	if os.path.exists(outdir): 
		print "\nError: Output directory already exists. Exiting" %(outdir)
		sys.exit()

	if len(params['pdb_list']) == 0: 
		if len(params['hhr']) == 0: 
                	print "\nError: Either .hhr or .pdb files must be specified. Exiting.\n" 
                	sys.exit()
	if params['em_map']: 
		if not os.path.exists(params['em_map']):
                	print "\nError: input EM map %s doesn't exist, exiting.\n" %(params['em_map'])
                	sys.exit()
	if params['relax'] is False:
		if not params['fasta']: 
			print "\nError: FASTA file is required for input, exiting.\n" 
                        sys.exit()
		if not os.path.exists(params['fasta']):
                	print "\nError: input FASTA file %s doesn't exist, exiting.\n" %(params['fasta'])
                	sys.exit()      
	if params['em_map']:
		volsize=os.path.getsize(params['em_map'])/1000000

	if params['em_map']:
		if volsize >250: 
			print 'Error: Volume size is too large - did you try cutting out extra density to make a smaller volume?'
			sys.exit()

	if len(params['pdb_list']) > 0: 
		pdb_read = open(params['pdb_list'], 'r')
        	for pdbline in pdb_read:
                	splitPdb = pdbline.split()
                	if not splitPdb[0] == '':
                        	if not os.path.exists(str(splitPdb[0])):
                                	print 'Error:Reference pdb file %s does not exist in current directory. Exiting.' %(splitPdb[0])
                                	sys.exit()

	if not params['em_map']: 
		volsize=''
	return volsize,os.path.dirname(os.path.abspath( __file__ ))

#================================================
if __name__ == "__main__":

	params=setupParserOptions()

	if params['num_models'] % 36 == 0: 
		numInstances=float(params['num_models']/36)
		numthreads=params['num_models_per_instance']
		numToRequest=numthreads

	if params['num_models'] % 36 != 0: 
		numInstances=float(params['num_models'])/36+1
                numthreads=params['num_models_per_instance']	
		numToRequest=numthreads

	if params['relax'] is True: 
		numInstances=1
		numthreads=params['num_models_per_instance']
		numToRequest=numthreads

	if len(params['outdir']) == 0:
	        startTime=datetime.datetime.utcnow()
 		params['outdir']=startTime.strftime('%Y-%m-%d-%H%M%S')
		if params['relax'] is False: 
			params['outdir']=params['outdir']+'-Rosetta-CM'
		if params['relax'] is True:
                        params['outdir']=params['outdir']+'-Rosetta-Relax'
	volsize,rosettadir=checkConflicts(params,params['outdir'])
	awsdir='%s/../aws/' %(rosettadir)

	#Make output directory
	os.makedirs(params['outdir'])
	
	#Prepare input files
	#Skip if PDB list provided
	if len(params['pdb_list']) == 0:  

		print '\nFormatting input .hrr and .fasta files to create PDB files for docking into density...\n'

		cmd='./rosetta_prepare_initial_alignment.py --align_list=%s --fasta=%s\n' %(params['hhr'],params['fasta'])
		subprocess.Popen(cmd,shell=True).wait()

		cmd='mv alignments.filt %s/'%(params['outdir'])
		subprocess.Popen(cmd,shell=True).wait()

		if params['nocheck'] is True: 

			o1=open('%s/pdb_list.txt' %(params['outdir']),'w')

			outputfiles=sorted(glob.glob('%s/*_2*pdb' %(params['outdir'])))
			for outputfile in outputfiles: 
				o1.write('%s\t\t1\n' %(outputfile))

			o1.close()
		#Make PDB LIST file '%s/pdb_list.txt' %(params['outdir'])
		print '...finished with file preparation, shutting down instance\n'
		if params['nocheck'] is False: 
			print 'Please dock each of these PDB files into your density (e.g. using UCSF Chimera) and then save into a text file to be provided as --pdb_list for Rosetta-CM or Rosetta-relax:\n'
			for pdbfile in sorted(glob.glob('%s/*_2*pdb' %(params['outdir']))): 
				print '%s' %(pdbfile)
			print '\n'
			sys.exit()

	print '\n\nStarting Rosetta model refinement in the cloud ...\n'
	
	if params['pdb_list'].split('.')[-1] == 'txt': 
		pdb_list=params['pdb_list']
	if len(params['pdb_list']) == 0: 
		if not os.path.exists('%s/pdb_list.txt' %(params['outdir'])): 
			print 'Error: PDB files were not correctly generated by Rosetta preparation script.Exiting\n'
			sys.exit()
		pdb_list='%s/pdb_list.txt' %(params['outdir'])

	if params['relax'] == True:
		if params['sym'] != "C1": 
			cmd='%s/rosetta_prepare_input_files_incl_symm.py --pdb_list=%s --em_map=%s --num=1 -r --symm=%s --outdir=%s/' %(rosettadir,pdb_list,params['em_map'],params['sym'],params['outdir'])				     
			if params['debug'] is True: 
                       		print cmd 
                	subprocess.Popen(cmd,shell=True).wait()	
		if params['sym'] == 'C1': 
			cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s -r --outdir=%s/ %s'  %(rosettadir,pdb_list,params['em_map'],params['outdir'])
			if params['debug'] is True: 
				print cmd 
			subprocess.Popen(cmd,shell=True).wait()

	if params['relax'] == False:
                cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s --fasta=%s --outdir=%s/'  %(rosettadir,pdb_list,params['em_map'], params['fasta'],params['outdir'])
		if params['debug'] is True: 
                        print cmd
		subprocess.Popen(cmd,shell=True).wait()

	#Error check
	if not os.path.exists('%s/run_final.sh' %(params['outdir'])): 
		print 'Error: Rosetta file preparation failed, was unable to create %s/run_final.sh. Exiting' %(params['outdir'])
		sys.exit()
	if params['relax'] == False:
		if not os.path.exists('%s/hybridize_final.xml' %(params['outdir'])): 
			print 'Error: Rosetta file preparation failed, was unable to create %s/hybridize_final.xml. Exiting' %(params['outdir'])
			sys.exit()
	if params['relax'] == True:
                if not os.path.exists('%s/relax_final.xml' %(params['outdir'])):
                        print 'Error: Rosetta file preparation failed, was unable to create %s/relax_final.xml. Exiting' %(params['outdir'])
                        sys.exit()

	print 'Starting Rosetta job..'

        now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute

	#Upload data
	cmd='chmod +x %s/run_final.sh' %(params['outdir'])
	subprocess.Popen(cmd,shell=True).wait()

        cmd='/usr/local/bin/parallel -j%i ./run_final.sh {} ::: {1..%i}> /home/ubuntu/rosetta.out 2> /home/ubuntu/rosetta.err < /dev/null &"' %(numthreads,numthreads)
	subprocess.Popen(cmd,shell=True)
	
	sys.exit()
	#Start waiting script: Should be in teh background so users can log out
	print '\nRosetta job submitted on AWS! Monitor output file: %s/rosetta.out to check status of job\n\n' %(params['outdir'])

	cmd='touch %s/rosetta.out' %(params['outdir'])
	subprocess.Popen(cmd,shell=True).wait()

	#Write instance, volume, and IP lists
	with open('%s/instanceIPlist.txt' %(params['outdir']),'wb') as fp: 
		pickle.dump(instanceIPlist,fp)
	with open('%s/instanceIDlist.txt' %(params['outdir']),'wb') as fp:
                pickle.dump(instanceIDlist,fp)
	if params['relax'] is False:
		rosettaflag='cm'
	if params['relax'] is True:
                rosettaflag='relax'

	pdbfilename=linecache.getline(pdb_list,1).split()[0].strip()

	cmd='%s/rosetta_waiting.py --instanceIPlist=%s/instanceIPlist.txt --instanceIDlist=%s/instanceIDlist.txt --numModels=%i --numPerInstance=%i --outdir=%s --pdbfilename=%s --type=%s&' %(rosettadir,params['outdir'],params['outdir'],numToRequest,numthreads,params['outdir'],pdbfilename,rosettaflag)
	if params['debug'] is True: 
		print cmd 
	subprocess.Popen(cmd,shell=True)

