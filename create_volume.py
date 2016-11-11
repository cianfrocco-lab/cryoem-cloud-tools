#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) < 4:
	print '\nUsage: aws_ebs_create [size in GB] [zone] "Description in double quotes"\n'
	print '\nSpecify size of EBS volume to be created (in GB) along with availability zone (e.g. us-east-1b) and description provided in double quotes\n'
	sys.exit()

volSize=sys.argv[1]
AZ=sys.argv[2]
allowedZones=['us-east-1b','us-east-1c','us-east-1d','us-east-1e','us-west-2a','us-west-2b','us-west-2c']
description=sys.argv[3]

if AZ not in allowedZones:
	print '\nError: Specified zone %s not in approved list:' %(AZ)
	print allowedZones
	print '\n'
	sys.exit() 

if  float(volSize) > 500: 
	print 'Error: Volume size too large %s GB' %(volSize)
	sys.exit()
 
#==============================
def query_yes_no(question, default="yes"):
	valid = {"yes": True, "y": True, "ye": True,"no": False, "n": False}
	if default is None:
		prompt = " [y/n] "
	elif default == "yes":
		prompt = " [Y/n] "
	elif default == "no":
		prompt = " [y/N] "
	else:
		raise ValueError("invalid default answer: '%s'" % default)
	while True:
		sys.stdout.write(question + prompt)
		choice = raw_input().lower()
		if default is not None and choice == '':
			return valid[default]
		elif choice in valid:
			return valid[choice]
		else:
			sys.stdout.write("Please respond with 'yes' or 'no' "
					 "(or 'y' or 'n').\n")


#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

answer=query_yes_no("\nCreate volume in %s that is %s GB?" %(AZ,volSize))

if answer is True:

	print '\nCreating volume ...\n'

	volID=subprocess.Popen('aws ec2 create-volume --size %s --availability-zone %s --volume-type gp2 | grep VolumeId' %(volSize,AZ),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value=%s' %(volID,tag)
	subprocess.Popen(cmd,shell=True).wait()	
	
	cmd='aws ec2 create-tags --resources %s --tags Key=Name,Value="%s"' %(volID,description)
	subprocess.Popen(cmd,shell=True).wait()
