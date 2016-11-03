#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) < 3:
	print '\nUsage: aws_ebs_attach [instance ID] [volume ID]\n'
	print '\nAttach EBS volume to instance.\n'
	sys.exit()

volID=sys.argv[2]
instanceID=sys.argv[1]

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

print '\nAttaching volume %s to instance %s ...\n' %(volID,instanceID)

volID=subprocess.Popen('aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdh' %(volID,instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()


