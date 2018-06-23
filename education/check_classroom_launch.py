#!/usr/bin/env python

import random
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
        parser.set_usage("This program will start a classroom of virtual machines on AWS")
        parser.add_option("--instancelist",dest="instancelist",type="string",metavar="InstanceList",
                    help="AWS instance list file generated from launch_classroom.py")
	parser.add_option("--s3bucket",dest="bucket",type="string",metavar="bucket",
                    help="Optional: Provide s3 bucket name to confirm files transferred")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
            help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) == 1:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#================================================
if __name__ == "__main__":

        params=setupParserOptions()
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	instanceIPlist=[]
	instanceidlist=[]
	ebs1list=[]
	ebs2list=[]
	userlist=[]
	passwordlist=[]
	for line in open(params['instancelist'],'r'):
                if 'Information' in line:
                        continue
                instanceIPlist.append(line.split()[2])
		instanceidlist.append(line.split()[3])
		userlist.append(line.split()[0])
		passwordlist.append(line.split()[1])

	outfile='%s_check%i.txt' %(params['instancelist'][:-4],int(time.time()))
	o1=open(outfile,'w')

	#To check: instance running, EBS volumes attached, size of data in directories matches with S3 folder sizes
	counter=0
	s3tutorialsize=subprocess.Popen("aws s3 ls --recursive --summarize university-of-michigan-cryoem-workshop/ | grep Size:",shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1] #bytes
	
	while counter < len(instanceIPlist): 

		#Check instance state
		instanceStatus=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{State:State}" | grep Name' %(instanceidlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		SysStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(instanceidlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                InsStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(instanceidlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

		tutorialsize=subprocess.Popen("ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'du -s /tutorial/ | cut -f1'" %(keypair,instanceIPlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip() #bytes
		usersize=subprocess.Popen("ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'du -s /userdata/ | cut -f1'" %(keypair,instanceIPlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip() #bytes
		s3usersize=subprocess.Popen("aws s3 ls --recursive --summarize %s/%s | grep Size:" %(params['bucket'],userlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1] #bytes
		if float(s3usersize)==0: 
			s3usersize=1
		o1.write('%s=%s (%s,%s)\t%s\t%s\t%f\t%s\t%s\t%f\n' %(instanceidlist[counter],instanceStatus,SysStatus,InsStatus,float(tutorialsize)*1000,float(s3tutorialsize)/100,float(float(tutorialsize)*1000/float(s3tutorialsize)/100)*100,usersize,s3usersize,float(float(usersize)/float(s3usersize))*100))
		counter=counter+1
	o1.close()	
