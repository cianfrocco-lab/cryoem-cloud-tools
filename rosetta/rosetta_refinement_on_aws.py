#!/usr/bin/env python

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
        parser.set_usage("This program will submit a rosetta atomic model refinement to AWS for refinement. Specify input pdb file(s), FASTA file and cryo-EM maps below.\n\n%prog --pdb_list=<.txt file with the list of input pdbs and their weights> --fasta=<FASTA file with protein sequence> --em_map=<EM map in .mrc format> --num=<number of atomic structures per CPU process (default:5) -r (flag to run relax instead of CM)")
        parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",
                    help=".txt file with the input pdbs and their weights")
        parser.add_option("--em_map",dest="em_map",type="string",metavar="FILE",
                    help="EM map in .mrc format")
	parser.add_option("--fasta",dest="fasta",type="string",metavar="FILE",
                    help="FASTA sequence file (not required for rosetta relax)")
	parser.add_option("--AMI",dest="AMI",type="string",metavar="AMI",
                    help="AMI for Rosetta software environment on AWS. (Read more here: cryoem-tools.cloud/rosetta-aws)")
	parser.add_option("-r", action="store_true",dest="relax",default=False,
                    help="run rosetta relax instead of CM")
	parser.add_option("--outdir",dest="outdir",type="string",metavar="DIR",default='',
		    help="Optional: Name of output directory. Otherwise, output directory will be automatically generated")
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
	
	if os.path.exists(outdir): 
		print "\nError: Output directory already exists. Exiting" %(outdir)
		sys.exit()

        if not os.path.exists(params['pdb_list']):
                print "\nError: input pdb list %s doesn't exist, exiting.\n" %(params['pdb_list'])
                sys.exit()
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
	volsize=os.path.getsize(params['em_map'])/1000000

	if volsize >250: 
		print 'Error: Volume size is too large - did you try cutting out extra density to make a smaller volume?'
		sys.exit()

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

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

	return volsize,awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir

#================================================
if __name__ == "__main__":

	##Hard coded values
	sizeneeded=100
	instance='m4.xlarge'
	numthreads=4
	loadMin=5
	numToRequest=4
        params=setupParserOptions()

	if numToRequest % numthreads != 0:
                numToRequest=numthreads*((numToRequest % numthreads)+1)
		
	numInstances=(numToRequest/numthreads)
	print numInstances
	if len(params['outdir']) == 0:
	        startTime=datetime.datetime.utcnow()
 		params['outdir']=startTime.strftime('%Y-%m-%d-%H%M%S')
		if params['relax'] is False: 
			params['outdir']=params['outdir']+'-cm'
		if params['relax'] is True:
                        params['outdir']=params['outdir']+'-r'
	volsize,awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir=checkConflicts(params,params['outdir'])

	#Make output directory
	os.makedirs(params['outdir'])
	
	project=''
        #Get project name if exists
        if os.path.exists('.aws_relion_project_info'):
                project=linecache.getline('.aws_relion_project_info',1).split('=')[-1]

	#Prepare input files
	if params['relax'] == True:
		cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s -r --outdir=%s/'  %(rosettadir,params['pdb_list'],params['em_map'],params['outdir'])
		subprocess.Popen(cmd,shell=True).wait()

	if params['relax'] == False:
                cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s --fasta=%s --outdir=%s/'  %(rosettadir,params['pdb_list'],params['em_map'], params['fasta'],params['outdir'])
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

	#Create EBS volume
	counter=0
	volIDlist=[]
	while counter < numInstances: 
        	cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%0.f"'%(awsdir,sizeneeded,awsregion,teamname,time.time())+'> %s/awsebs_%i.log'%(params['outdir'],counter)
	        subprocess.Popen(cmd,shell=True).wait()
        	###Get volID from logfile
	        volID=linecache.getline('%s/awsebs_%i.log'%(params['outdir'],counter),5).split('ID: ')[-1].split()[0]
	        print volID
		volIDlist.append(volID)
		time.sleep(10)
		counter=counter+1
	print '\nLaunching %i virtual machine(s) %s on AWS in region %sa (initialization will take a few minutes)\n' %(numInstances,instance,awsregion)

	counter=0	
	while counter < numInstances:
		#Launch instance
        	cmd='%s/launch_AWS_instance.py --instance=%s --availZone=%sa --volume=%s --AMI=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,volID,params['AMI'],params['outdir'],counter)
	        subprocess.Popen(cmd,shell=True)
        	time.sleep(10)
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

	print '\nUploading files to AWS ...\n'

	counter=0
	while counter < numInstances: 
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/run_final.sh ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True).wait()
	
		if params['relax'] == False:
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/hybridize_final.xml ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
        		subprocess.Popen(cmd,shell=True).wait()
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['fasta'],instanceIPlist[counter])
        		subprocess.Popen(cmd,shell=True).wait()
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,params['em_map'],instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True).wait()
	
		if params['relax'] == True:
			cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/relax_final.xml ubuntu@%s:~/'%(keypair,params['outdir'],instanceIPlist[counter])
	                subprocess.Popen(cmd,shell=True).wait()

		#Transfer PDB files
		pdb_read = open(params['pdb_list'], 'r')
		for pdbline in pdb_read:
			splitPdb = pdbline.split()
	                if not splitPdb[0] == '':
				cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,str(splitPdb[0]),instanceIPlist[counter])
				subprocess.Popen(cmd,shell=True).wait()

		#Run job
        	cmd='ssh  -o "StrictHostKeyChecking no" -q -n -f -i %s ubuntu@%s "export PATH=/usr/bin/$PATH && export PATH=/home/Rosetta/2017_08/main/source/:$PATH && ./run_final.sh > /home/ubuntu/rosetta.out 2> /home/ubuntu/rosetta.err < /dev/null &"' %(keypair,instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True)

	#Start waiting script: Should be in teh background so users can log out
	print 'Rosetta job submitted on AWS! Monitor output file: %s/rosetta_output.out to check status of job\n' %(params['outdir'])

	sys.exit()
	#Start monitoring status
	startTime=datetime.datetime.utcnow()
	time.sleep(60)

	isdone=0
	while isdone == 0:
		#If cloudwatch has load < 5% BUT there aren't finished PDBs yet, job crashed. Terminate.
		currentTime=datetime.datetime.utcnow()
		if os.path.exists('%s/cloudwatchtmp.log'%(params['outdir'])): 
			os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
		cmd='aws cloudwatch get-metric-statistics --metric-name CPUUtilization --start-time %s  --period 300 --namespace AWS/EC2 --statistics Average --dimensions Name=InstanceId,Value=%s --end-time %s > %s/cloudwatchtmp.log' %(startTime.strftime('%Y-%m-%dT%H:%M:00'),instanceID,currentTime.strftime('%Y-%m-%dT%H:%M:00'),params['outdir'])
		subprocess.Popen(cmd,shell=True).wait()
		o1=open('%s/cloudwatchtmp.log'%(params['outdir']),'r')
		for line in o1: 
			if len(line.split())>0:
				if line.split()[0] == '"Average":': 
					load=float(line.split()[1][:-1])
					if load < loadMin: 
						print 'finished'
						#Download all pdb files, take note if you didn't download enough files consdiering number of models requested


						isdone=1
		o1.close()
		os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
		time.sleep(60)

	print 'Rosetta refinement finished. Shutting down instance.'

	cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,params['outdir'])
        subprocess.Popen(cmd,shell=True).wait()

        isdone=0
        while isdone == 0:
              status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
              if status == 'terminated':
                    isdone=1
              time.sleep(10)

	cmd='aws ec2 delete-volume --volume-id %s > %s/tmp4949585940.txt' %(volID,params['outdir'])
        subprocess.Popen(cmd,shell=True).wait()	

	now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1

