#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) < 4:
	print '\nUsage: aws_ebs_create [size in GB] [zone] "Description in double quotes" [snapshot ID]\n'
	print '\nSpecify size of EBS volume to be created (in GB) along with availability zone (e.g. us-east-1b) and description provided in double quotes\n'
	sys.exit()

if len(sys.argv) == 4: 
	volSize=sys.argv[1]
	AZ=sys.argv[2]
	allowedZones=['us-east-1a','us-east-1b','us-east-1c','us-east-1d','us-east-1e','us-east-1f','us-west-2a','us-west-2b','us-west-2c','eu-west-1a','eu-west-1b','eu-west-1c','us-east-2a','us-east-2b','us-east-2c']
	description=sys.argv[3]
	snapid=''

if len(sys.argv) == 5:
        volSize=sys.argv[1]
        AZ=sys.argv[2]
        allowedZones=['us-east-1a','us-east-1b','us-east-1c','us-east-1d','us-east-1e','us-east-1f','us-west-2a','us-west-2b','us-west-2c','eu-west-1a','eu-west-1b','eu-west-1c','us-east-2a','us-east-2b','us-east-2c']
        description=sys.argv[3]
	snapid=' --snapshot-id %s' %(sys.argv[4])

if AZ not in allowedZones:
	print '\nError: Specified zone %s not in approved list:' %(AZ)
	print allowedZones
	print '\n'
	sys.exit() 

if  float(volSize) > 16000: 
	print 'Error: Volume size too large %s GB' %(volSize)
	sys.exit()
 
#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

print '\nCreating volume ...\n'

volID=subprocess.Popen('aws ec2 create-volume --size %s --availability-zone %s --volume-type gp2 %s | grep VolumeId' %(volSize,AZ,snapid),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value=%s' %(volID,tag)
subprocess.Popen(cmd,shell=True).wait()	
	
print '\nID: %s' %(volID)

cmd='aws ec2 create-tags --resources %s --tags Key=Name,Value="%s"' %(volID,description)
subprocess.Popen(cmd,shell=True).wait()
