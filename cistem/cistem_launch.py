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
        parser.set_usage("This program will submit a rosetta atomic model refinement to AWS for refinement. Specify input pdb file(s), FASTA file and cryo-EM maps below.\n\n%prog --pdb_list=<.txt file with the list of input pdbs and their weights> --fasta=<FASTA file with protein sequence> --em_map=<EM map in .mrc format> --num=<number of atomic structures per CPU process (default:5) -r (flag to run relax instead of CM)")
        parser.add_option("--outdir",dest="outdir",type="string",metavar="FILE",
                    help="path")
	options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) <= 1:
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
		print "\nError: Output directory already exists. Exiting" 
		sys.exit()

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
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

	return awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir

#================================================
if __name__ == "__main__":

	params=setupParserOptions()

	AMI='ami-711e3714'

	instance='m4.large'
        numthreads=1
	numToRequest=numthreads

	if len(params['outdir']) == 0:
	        startTime=datetime.datetime.utcnow()
 		params['outdir']=startTime.strftime('%Y-%m-%d-%H%M%S')
	
	awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir=checkConflicts(params,params['outdir'])

	#Make output directory
	os.makedirs(params['outdir'])
	
        #Launch instance
	counter=0
	cmd='%s/launch_AWS_instance.py --noEBS --instance=%s --availZone=%sa --AMI=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,AMI,params['outdir'],counter)
	subprocess.Popen(cmd,shell=True)
	time.sleep(20)
      
     	instanceIDlist=[]
        instanceIPlist=[]
        
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

	cmd='ssh  -nNT -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -L 5901:localhost:5901 -i %s ubuntu@%s &'  %(keypair,instanceIPlist[0])
	subprocess.Popen(cmd,shell=True).wait()

	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null  -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "/usr/bin/vncserver &"' %(keypair,instanceIPlist[0])
	subprocess.Popen(cmd,shell=True).wait()

	print 'testing'

	print 'ready for connection! Input localhost:5901 into VNC Viewer and pw cryoem'

