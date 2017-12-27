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
from awsdatatransfer import * 

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("This program will start a virtual machine on AWS to run cisTEM, syncing all contents of the current directory to AWS")
        parser.add_option("--instance",dest="instance",type="string",metavar="Instance",default='t2.micro',
                    help="Instance type on AWS")
	parser.add_option("--run",action="store_true",dest="run",default=False,
            help="Launch cisTEM on AWS")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
            help="debug")	
	options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
	if len(sys.argv) < 1:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        if params['run'] is False: 
		parser.print_help()
                sys.exit()
	return params

#=============================
def checkConflicts(params):

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','run.err')
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

	if awsregion == 'us-east-2': 
		AMI='ami-b997bfdc'

	instance=params['instance']
	if params['debug'] is True: 
		print instance
	errorflag=0
	if 'g3' in instance: 
		errorflag=1
	if 'g2' in instance: 
		errorflag=1
	if 'p2' in instance: 
		errorflag=1
	if 'p3' in instance:
		errorflag=1
	if errorflag == 1:  
		print 'Error: cisTEM is not GPU-accelerated. Please specify an alterative instance for cisTEM (e.g. m4 instances)'
		sys.exit()

	if 'm4' in instance: 
		numToRequest=10
	if 't2' in instance: 
		numToRequest=2	
	return awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest

#================================================
if __name__ == "__main__":

	params=setupParserOptions()
	
	#Get number of CPUs on current machine
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
		numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
        if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())

	awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest=checkConflicts(params)

	#Get correct rclone
        if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                rclonepath='%s/rclone' %(awsdir)
        if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                rclonepath='%s/rclone_mac'%(awsdir)

	#Move data up to S3
        directoryToTransfer=os.getcwd()
	numfiles=1
	maxFileSize=1
	bucketname='rln-aws-tmp-%s-%s/%s' %(teamname,keypair.split('/')[-1].split('.')[0],directoryToTransfer)
	transferDirToS3(directoryToTransfer,bucketname,awsdir,numCPUs*2,key_ID,secret_ID,awsregion)

	print '\nLaunching instance %s on AWS for cisTEM (will take 2 - 5 minutes)...' %(instance)
	
        #Launch instance
	counter=0
	cmd='%s/launch_AWS_instance.py --noEBS --instance=%s --availZone=%sa --AMI=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,AMI,directoryToTransfer,counter)
	subprocess.Popen(cmd,shell=True)
	time.sleep(20)
     
	#Wait for instance to boot up 
     	instanceIDlist=[]
        instanceIPlist=[]
	isdone=0
        qfile='%s/awslog_%i.log' %(directoryToTransfer,counter)
       	while isdone == 0:
        	r1=open(qfile,'r')
                for line in r1:
                	if len(line.split()) == 2:
                        	if line.split()[0] == 'ID:':
                                	isdone=1
                r1.close()
       	        time.sleep(10)

	#Get IP address
        instanceIDlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ID'%(directoryToTransfer,counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1].strip())
	keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(directoryToTransfer,counter), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        instanceIPlist.append(subprocess.Popen('cat %s/awslog_%i.log | grep ssh'%(directoryToTransfer,counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip())

	os.remove('%s/awslog_%i.log' %(directoryToTransfer,counter))

	print '\nSetting everything up on AWS...'

	#Start VNC server
	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "/usr/bin/vncserver :1"' %(keypair,instanceIPlist[0])
	subprocess.Popen(cmd,shell=True).wait()

	#Create path on local machine
	cmd='touch %s/.tmp' %(os.getcwd())
	subprocess.Popen(cmd,shell=True).wait()

	cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -R -e "ssh -q -o StrictHostKeyChecking=no -i %s" %s/.tmp ubuntu@%s:~/ > %s/rsync.log' %(os.getcwd(),keypair,os.getcwd(),instanceIPlist[0],os.getcwd())
	if params['debug'] is True: 
		print cmd
	subprocess.Popen(cmd,shell=True).wait()

	if os.path.exists('%s/rsync.log' %(os.getcwd())): 
		os.remove('%s/rsync.log' %(os.getcwd()))

	#Move directory to / location
	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "sudo mv %s /"' %(keypair,instanceIPlist[0],os.getcwd().split('/')[1])
	if params['debug'] is True: 
		print cmd 
	subprocess.Popen(cmd,shell=True).wait()

	#Move data down to instance
	transferS3toVM(instanceIPlist[0],keypair,bucketname,os.getcwd(),'%s/rclone' %(awsdir),key_ID,secret_ID,awsregion,numfiles,maxFileSize)

	cmd="ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'echo" %(keypair,instanceIPlist[0])+" cd %s >> ~/.bashrc'" %(os.getcwd())
	if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()

	#Edit .bashrc file to have automatic cd into cisTEM directory
	print "\n\n\n"
	print "Your cisTEM instance is ready to use! In order to use this machine:"
	print "1. Please copy and paste into your terminal:"
	print 'ssh -L 5901:localhost:5901 -o LogLevel=quiet -o UserKnownHostsFile=/dev/null  -o StrictHostKeyChecking=no -i %s ubuntu@%s' %(keypair,instanceIPlist[0])
	print "2. Open VNC viewer and connect to localhost:1"
	print "3. Open NEW terminal on AWS instance and you should be in the same directory as the directory from where the script was launched"
	print '\n4. When finished with cisTEM on AWS, log out of terminal by typing:'
	print '$ exit'
	print '$ cistem_terminate'
