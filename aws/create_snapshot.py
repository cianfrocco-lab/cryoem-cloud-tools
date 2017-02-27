#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) < 2:
	print '\nUsage: aws_snapshot_create [volume ID]"\n'
	sys.exit()

if len(sys.argv) == 2: 
	volID=sys.argv[1]
	addition=''
if len(sys.argv) == 3:
	volID=sys.argv[1]
	addition=sys.argv[2]
 
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

#if answer is True:
print '\nStarting snapshot creation from EBS volume ...\n'

#Get vol description first
description=subprocess.Popen('aws ec2 describe-volumes  --volume-ids %s --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[0].Tags[*].{Key:Key}" | grep Key' %(volID,tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()
count2=0
tagcounter=-1
while count2 < len(description):
	if description[count2] == '"Name"':
		value=subprocess.Popen('aws ec2 describe-volumes  --volume-ids %s --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[0].Tags[%i]" | grep Value' %(volID,tag,tagcounter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split(':')[1].split('"')[1]
        if description[count2] == '"Key":':
                tagcounter=tagcounter+1
	count2=count2+1

if os.path.exists('tmp333r3.txt'): 
	os.remove('tmp333r3.txt')

value=addition+value
cmd='aws ec2 create-snapshot --volume-id %s --description "%s"  > tmp333r3.txt' %(volID,value)
subprocess.Popen(cmd,shell=True).wait()

#parse output
for line in open('tmp333r3.txt','r'): 
	if len(line.split('"')) > 2: 
		if line.split('"')[1] == 'SnapshotId': 
			snapID=line.split('"')[3]
tag=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip().split('/')[-1].split('.')[0]
cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value="%s"' %(snapID,tag)
subprocess.Popen(cmd,shell=True).wait()

if os.path.exists('tmp333r3.txt'): 
	os.remove('tmp333r3.txt')

print 'Snapshot ID: %s' %(snapID)
