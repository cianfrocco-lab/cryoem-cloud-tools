#!/usr/bin/env python

import subprocess
import os
import sys 

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

#Get number of instances to loop over
numInstances=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[*].Instances[*].{InstanceID:InstanceId}" | grep InstanceID | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\nInstanceType\tAvail. Zone\tInstanceID\tUser\tStatus'
print '-------------------------------------------------------------------------'

if float(numInstances) == 0:
	print 'No instances found\n'
	sys.exit()

while counter < float(numInstances): 

	instanceID=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{InstanceID:InstanceId}" | grep InstanceID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	status=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{State:State}" | grep Name' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	instanceType=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{Type:InstanceType}" | grep Type' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*]" | grep AvailabilityZone' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	
	print '%s\t%s\t%s\t%s\t%s' %(instanceType,availZone,instanceID,tag,status)

	counter=counter+1

#Info needed: instance ID, AMI, region, zone, tag

print '\n'
