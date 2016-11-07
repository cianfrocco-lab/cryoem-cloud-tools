#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) ==1:
	print '\nUsage: awskill [instance ID or cluster name]\n'
	print '\nSpecify instance ID or cluster name that will be terminated, which can be found using "awsls" or "awsls -c"\n'
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

starcluster=subprocess.Popen('which starcluster',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
if len(starcluster) == 0:
	clusterflag=0
if len(starcluster) > 0: 
	clusterflag=1
if not os.path.exists('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())):
        os.makedirs('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()))

if not os.path.exists('%s/.starcluster/config' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())):
        AWS_ACCESS_KEY_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_SECRET_ACCESS_KEY=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_ACCOUNT_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        cmd='####################################\n'        
	cmd+='## StarCluster Configuration File ##\n'
        cmd+='####################################\n'        
	cmd+='[aws info]\n'
        cmd+='AWS_USER_ID=%s\n' %(AWS_ACCOUNT_ID)
        cmd+='AWS_ACCESS_KEY_ID =%s\n' %(AWS_ACCESS_KEY_ID)
        cmd+='AWS_SECRET_ACCESS_KEY = %s\n' %(AWS_SECRET_ACCESS_KEY)        
	cmd+='AWS_REGION_NAME = %s\n' %(AWS_DEFAULT_REGION)
        cmd+='AVAILABILITY_ZONE = %s\n' %(params['zone'])
        cmd+='AWS_REGION_HOST = ec2.%s.amazonaws.com\n' %(AWS_DEFAULT_REGION)
        cmd+='[global]\n'
        cmd+='DEFAULT_TEMPLATE=cluster\n'
        cmd+='[key %s]\n' %(keyPath.split('/')[-1].split('.')[0])
        cmd+='KEY_LOCATION=%s\n' %(keyPath)

	o1=open('%s/.starcluster/config' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()),'w')
        o1.write(cmd)
        o1.close()

if instanceID.split('-')[0] == 'cluster':

	if clusterflag==0: 
		print 'Error: Could not find starcluster installed. Exiting.\n'
		sys.exit()

	cmd='starcluster terminate %s -f'%(instanceID)
	subprocess.Popen(cmd,shell=True).wait()

if instanceID.split('-')[0] != 'cluster':

	answer=query_yes_no("\nTerminate instance %s?" %(instanceID))

	if answer is True:

		print '\nRemoving instance ...\n'

		if os.path.exists('tmp4949585940.txt'):
			os.remove('tmp4949585940.txt')

		cmd='aws ec2 terminate-instances --instance-ids %s > tmp4949585940.txt' %(instanceID)
		subprocess.Popen(cmd,shell=True).wait()

		os.remove('tmp4949585940.txt')
	
