#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) ==1:
	print '\nUsage: awskill [instance ID]\n'
	print '\nSpecify instance ID that will be terminated, which can be found using "awsls"\n'
	sys.exit()

instanceID=sys.argv[1]

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

answer=query_yes_no("\nTerminate instance %s?" %(instanceID))

if answer is True:

	print '\nRemoving instance ...\n'

	if os.path.exists('tmp4949585940.txt'):
		os.remove('tmp4949585940.txt')

	cmd='aws ec2 terminate-instances --instance-ids %s > tmp4949585940.txt' %(instanceID)
	subprocess.Popen(cmd,shell=True).wait()

	os.remove('tmp4949585940.txt')
	
