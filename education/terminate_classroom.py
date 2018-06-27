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
                    help="AWS instance/volume list file generated from launch_classroom.py")
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

	instanceidlist=[]
	ebs1list=[]
	ebs2list=[]

	print "...shutting down instances..."

	for line in open(params['instancelist'],'r'): 
		if 'Information' in line: 
			continue
		instanceidlist.append(line.split()[3])
		ebs1list.append(line.split()[5])
		ebs2list.append(line.split()[7])

	counter=0
	while counter<len(instanceidlist): 

		cmd=subprocess.Popen('aws ec2 terminate-instances --instance-ids %s > tmp4949585940.txt' %(instanceidlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		counter=counter+1

	os.remove('tmp4949585940.txt')

	print "...waiting for instances to be terminated before EBS volumes are removed..."

	#Terminate instance
	counter=0
	while counter<len(instanceidlist): 
		isdone=0
                while isdone == 0:
                        status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceidlist[counter].strip()),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                        if status == 'terminated':
                                isdone=1
                        time.sleep(5)
                time.sleep(5)

                cmd='%s/kill_volume.py %s > awslog.log' %(awsdir,ebs1list[counter])
		subprocess.Popen(cmd,shell=True).wait()

		if '---' not in ebs2list[counter]: 
			cmd='%s/kill_volume.py %s > awslog.log' %(awsdir,ebs2list[counter])
			subprocess.Popen(cmd,shell=True).wait()

		os.remove('awslog.log') 
		
		counter=counter+1
