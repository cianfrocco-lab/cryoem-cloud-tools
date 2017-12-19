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
	parser.add_option("--AMI",dest="AMI",type="string",metavar="AMI",
                    help="AMI for Rosetta software environment on AWS. (Read more here: cryoem-tools.cloud/rosetta-aws)")
	parser.add_option("-r", action="store_true",dest="relax",default=False,
                    help="run rosetta relax instead of CM")
	parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",default='',
                    help="PDB reference file OR .txt file with the input pdbs and their weights. List is required Only required if no .hhr file provided")
	parser.add_option("--num",dest="num_models",type="int",metavar="INT",default=216,
                    help="Number of structures to calculate. (Default = 216)")
	parser.add_option("--num_per_VM",dest="num_models_per_instance",type="int",metavar="INT",default=36,
                    help="Number of structures to calculate per VM. (Default = 36)")
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
	if not params['AMI']: 
		print '\nError: No AMI specified. Exiting\n'
		sys.exit()
	if params['em_map']:
		volsize=os.path.getsize(params['em_map'])/1000000

	if params['em_map']:
		if volsize >250: 
			print 'Error: Volume size is too large - did you try cutting out extra density to make a smaller volume?'
			sys.exit()

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	if len(params['pdb_list']) > 0: 
		pdb_read = open(params['pdb_list'], 'r')
        	for pdbline in pdb_read:
                	splitPdb = pdbline.split()
                	if not splitPdb[0] == '':
                        	if not os.path.exists(str(splitPdb[0])):
                                	print 'Error:Reference pdb file %s does not exist in current directory. Exiting.' %(splitPdb[0])
                                	sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        rosettadir='%s/../rosetta/' %(awsdir)

	if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()
	
	if len(AWS_ID) == 0: 
		print 'Error: Could not find the environmental variable $AWS_ACCOUNT_ID. Exiting'
		sys.exit()
	if len(key_ID) == 0: 
		print 'Error: Could not find the environmental variable $AWS_ACCESS_KEY_ID. Exiting'
                sys.exit()
	if len(secret_ID) == 0:
		print 'Error: Could not find the environmental variable $AWS_SECRET_ACCESS_ID. Exiting'
                sys.exit()
	if len(teamname) == 0: 
		print 'Error: Could not find the environmental variable $RESEARCH_GROUP_NAME. Exiting'
                sys.exit()
	if len(keypair) == 0: 
		print 'Error: Could not find the environmental variable $KEYPAIR_PATH. Exiting'
                sys.exit()

	if not params['em_map']: 
		volsize=''
	return volsize,awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir

#================================================
if __name__ == "__main__":

	#Hard code parameters: 
	loadMin=5 #For monitoring load on machines to determine when rosetta finishes
	#numToRequest=2 
        
	params=setupParserOptions()

	if params['num_models'] % 36 == 0: 
		numInstances=float(params['num_models']/36)
		instance='c4.8xlarge'	
		numthreads=params['num_models_per_instance']
		numToRequest=numthreads

	if params['num_models'] % 36 != 0: 
		numInstances=float(params['num_models'])/36+1
		instance='c4.8xlarge'
                numthreads=params['num_models_per_instance']	
		numToRequest=numthreads

	if params['relax'] is True: 
		instance='m4.4xlarge'
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
	volsize,awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir=checkConflicts(params,params['outdir'])

	#Make output directory
	os.makedirs(params['outdir'])
	
	project=''
        #Get project name if exists
        if os.path.exists('.aws_relion_project_info'):
                project=linecache.getline('.aws_relion_project_info',1).split('=')[-1]

	#Prepare input files
	#Skip if PDB list provided
	if len(params['pdb_list']) == 0:  

		print '\nFormatting input .hrr and .fasta files to create PDB files for docking into density...\n'

		counter=0       
        	while counter < 1:
                	#Launch instance
	                cmd='%s/launch_AWS_instance.py --noEBS --instance=t2.micro --availZone=%sa --AMI=%s > %s/awslog_%i.log' %(awsdir,awsregion,params['AMI'],params['outdir'],counter)
        	        print '\n...booting up instance to format input files...\n' 
			subprocess.Popen(cmd,shell=True)
	                time.sleep(20)
			counter=counter+1
        
	        counter=0
        	instanceIDlist=[]
	        instanceIPlist=[]
        	while counter < 1:
                	isdone=0
	                qfile='%s/awslog_%i.log' %(params['outdir'],counter)
        	        while isdone == 0:
                	        r1=open(qfile,'r')
                        	for line in r1:
                                	if len(line.split()) == 2:
                                        	if line.split()[0] == 'ID:':
                                                	isdone=1
	                        r1.close()
        	                time.sleep(10)
                	instanceIDlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ID'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1].strip())
	                keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        	        instanceIPlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip())
                	counter=counter+1	

		#Move up files for preparing
		filesToUpload=['rosetta_prepare_initial_alignment.py','thread.sh','prepare_hybridize_from_hhsearch.pl']

		for uploadFile in filesToUpload: 

			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/%s ubuntu@%s:~/'%(keypair,rosettadir,uploadFile,instanceIPlist[0])
        		subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/'%(keypair,params['hhr'],instanceIPlist[0])
        	subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/'%(keypair,params['fasta'],instanceIPlist[0])
        	subprocess.Popen(cmd,shell=True).wait()

		#Create executable file
		o1=open('%s/run_prep.sh' %(params['outdir']),'w')
		o1.write('#!/bin/bash\n')
		o1.write('/bin/chmod +x prepare_hybridize_from_hhsearch.pl\n')
		o1.write('/bin/chmod +x rosetta_prepare_initial_alignment.py\n')
		o1.write('./rosetta_prepare_initial_alignment.py --align_list=%s --fasta=%s\n' %(params['hhr'],params['fasta']))
		o1.close()

		cmd='chmod +x %s/run_prep.sh' %(params['outdir'])
                subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/run_prep.sh ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[0])
		subprocess.Popen(cmd,shell=True).wait()

		cmd='ssh -o "StrictHostKeyChecking no" -q -n -f -i %s ubuntu@%s "export PATH=/usr/bin/$PATH && export PATH=/home/Rosetta/2017_08/main/source/:$PATH && ./run_prep.sh > /home/ubuntu/prep.out 2> /home/ubuntu/prep.err < /dev/null &"' %(keypair,instanceIPlist[0])
		subprocess.Popen(cmd,shell=True).wait()

		print '...running Rosetta file preparation on t2.micro instance...\n'
		
		time.sleep(30)
		#Wait to finish
		isdone=0
		while isdone == 0: 

			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/prep.out %s/' %(keypair,instanceIPlist[0],params['outdir'])
			subprocess.Popen(cmd,shell=True).wait()
					
			check=subprocess.Popen('cat %s/prep.out | grep rosetta_finished'%(params['outdir']), shell=True, stdout=subprocess.PIPE).stdout.read()
			if len(check) > 0:
				isdone=1

		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/*pdb %s/' %(keypair,instanceIPlist[0],params['outdir'])
                subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/alignments.filt %s/'%(keypair,instanceIPlist[0],params['outdir'])
		subprocess.Popen(cmd,shell=True).wait()

		#Kill instance
		cmd='%s/kill_instance.py %s > %s/aws.log' %(awsdir,instanceIDlist[0],params['outdir'])
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
                cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s --fasta=%s --outdir=%s/ %s'  %(rosettadir,pdb_list,params['em_map'], params['fasta'],params['outdir'])
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

	print 'Starting Rosetta job on %i x %s virtual machines on AWS in region %sa (initialization will take a few minutes)\n' %(numInstances,instance,awsregion)

	counter=0	
	while counter < numInstances:
		#Launch instance
        	cmd='%s/launch_AWS_instance.py --noEBS --instance=%s --availZone=%sa --AMI=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,params['AMI'],params['outdir'],counter)
	        subprocess.Popen(cmd,shell=True)
        	time.sleep(30)
		counter=counter+1
	
	counter=0
	instanceIDlist=[]
	instanceIPlist=[]
	while counter < numInstances:
        	isdone=0
	        qfile='%s/awslog_%i.log' %(params['outdir'],counter)
        	while isdone == 0:
        		r1=open(qfile,'r')
	                for line in r1:
        	        	if len(line.split()) == 2:
                	        	if line.split()[0] == 'ID:':
                        	                isdone=1
                	r1.close()
                	time.sleep(10)
        	instanceIDlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ID'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1].strip())
        	keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        	instanceIPlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(params['outdir'],counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip())
		counter=counter+1

        now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute

	#Upload data
	cmd='chmod +x %s/run_final.sh' %(params['outdir'])
	subprocess.Popen(cmd,shell=True).wait()

	print '...uploading files to AWS ...'

	counter=0
	while counter < numInstances: 
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/run_final.sh ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True).wait()
	
		if params['relax'] == False:
			if '.' in params['sym']: 
				cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['sym'],instanceIPlist[counter])
				subprocess.Popen(cmd,shell=True).wait()
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/hybridize_final.xml ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
        		subprocess.Popen(cmd,shell=True).wait()
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['fasta'],instanceIPlist[counter])
        		subprocess.Popen(cmd,shell=True).wait()
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['em_map'],instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True).wait()
	
		if params['relax'] == True:
			if '.' in params['sym']:
                                cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['sym'],instanceIPlist[counter])
                                subprocess.Popen(cmd,shell=True).wait()
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/relax_final.xml ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
	                subprocess.Popen(cmd,shell=True).wait()

		#Transfer PDB files
		pdb_read = open(pdb_list, 'r')
		for pdbline in pdb_read:
			splitPdb = pdbline.split()
	                if not splitPdb[0] == '':
				cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,str(splitPdb[0]),instanceIPlist[counter])
				subprocess.Popen(cmd,shell=True).wait()

		#Run job
        	cmd='ssh  -o "StrictHostKeyChecking no" -q -n -f -i %s ubuntu@%s "export PATH=/usr/bin/$PATH && export PATH=/home/Rosetta/2017_08/main/source/:$PATH && /usr/local/bin/parallel -j%i ./run_final.sh {} ::: {1..%i}> /home/ubuntu/rosetta.out 2> /home/ubuntu/rosetta.err < /dev/null &"' %(keypair,instanceIPlist[counter],numthreads,numthreads)
		print cmd 
		subprocess.Popen(cmd,shell=True)
	
		counter=counter+1

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

