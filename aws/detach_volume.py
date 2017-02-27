#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) < 2:
	print '\nUsage: aws_ebs_detach [volume ID]\n'
	print '\nDetach EBS volume from instance. Important to do before terminating instance\n'
	sys.exit()

volID=sys.argv[1]

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

print '\nDetaching volume %s ...\n' %(volID)

volID=subprocess.Popen('aws ec2 detach-volume --volume-id %s ' %(volID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()


