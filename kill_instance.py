#!/usr/bin/env python

import subprocess
import os
import sys 
if len(sys.argv) ==1:
	print '\nUsage: awskill [instance ID or cluster name]\n'
	print '\nSpecify instance ID or cluster name that will be terminated, which can be found using "awsls" or "awsls -c"\n'
	sys.exit()

instanceID=sys.argv[1]

#====================
def module_exists(module_name):
        try:
                __import__(module_name)
        except ImportError:
                return False
        else:
                return True

#====================
def exec_remote_cmd(cmd):
    with hide('output','running','warnings'), settings(warn_only=True):
        return run(cmd)

#==============================
def query_yes_no(question, default="no"):
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
        cmd+='AVAILABILITY_ZONE = %sa\n' %(AWS_DEFAULT_REGION)
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

	#answer=query_yes_no("\nTerminate instance %s?" %(instanceID))
        PublicIP=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

  	#Import Fabric modules now: 
   	fabric_test=module_exists('fabric.api')
        if fabric_test is False: 
                print 'Error: Could not find fabric installed and it is required. Install from here: http://www.fabfile.org/installing.html'
                sys.exit()
	from fabric.operations import run, put
   	from fabric.api import env,run,hide,settings 
   	from fabric.context_managers import shell_env
	from fabric.operations import put 

	env.host_string='ubuntu@%s' %(PublicIP)
	env.key_filename = '%s' %(keyPath)
	answer=True
	if answer is True:

		print '\nRemoving instance ...\n'

		if os.path.exists('tmp4949585940.txt'):
			os.remove('tmp4949585940.txt')

		#Check if instance has volume mounted aws ec2 describe-instance-attribute --instance-id i-0d4524ffad3ac020b --attribute blockDeviceMapping
		numDevices=float(subprocess.Popen('aws ec2 describe-instances --instance-id %s  --query "Reservations[*].Instances[*].BlockDeviceMappings" | grep DeviceName  | wc -l' %(instanceID), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])

		if numDevices > 1:
			counter=2
			while counter <= numDevices:
				mountpoint=subprocess.Popen('aws ec2 describe-instances --instance-id %s  --query "Reservations[*].Instances[*].BlockDeviceMappings[%i]"  | grep DeviceName' %(instanceID,counter-1), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split(':')[-1].split('"')[1]
				volID=subprocess.Popen('aws ec2 describe-instances --instance-id %s  --query "Reservations[*].Instances[*].BlockDeviceMappings[%i]" | grep VolumeId' %(instanceID,counter-1), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split(':')[-1].split('"')[1]
				
				umount=exec_remote_cmd('sudo umount /dev/%s' %(mountpoint))
				if len(umount.split()) >0:
					print 'Error unmounting volume. Stop all running processes (shown below) and try again to terminate instance.\n'
					lsof=exec_remote_cmd('lsof | grep /data') 
					if len(lsof)>0: 
						counter2=0
						print 'COMMAND\t\tPROCESSID'
						print '------------------------------'
						while counter2 < len(lsof.split('\n')):
							command=lsof.split('\n')[counter2].split()[0]
							pid=lsof.split('\n')[counter2].split()[1]

							print '%s\t\t%s' %(command,pid)
							counter2=counter2+1 
					print ''
					sys.exit()
				vol=subprocess.Popen('aws ec2 detach-volume --volume-id %s ' %(volID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	
				counter=counter+1
		cmd='aws ec2 terminate-instances --instance-ids %s > tmp4949585940.txt' %(instanceID)
		subprocess.Popen(cmd,shell=True).wait()
		os.remove('tmp4949585940.txt')

		print 'Success!'	
