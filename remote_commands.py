#!/usr/bin/env python
import subprocess
import os
import sys
from fabric.operations import run, put
from fabric.api import env,run,hide,settings
from fabric.context_managers import shell_env
from fabric.operations import put
from cryptography.fernet import Fernet

#====================
def exec_remote_cmd(cmd):
    with hide('output','running','warnings'), settings(warn_only=True):
        return run(cmd)

def runThisStuff():
#Setup
	homepath=subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	nProcsPerInstance=3
	keyPath='/home/michaelc/.aws/mike_oregon.pem'
	AWS_ACCESS_KEY_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	AWS_SECRET_ACCESS_KEY=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	AWS_ACCOUNT_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	params={}
	params['s3']='leschziner-s3-test'
	instanceDict={'i-0386bff3bc6153efd': '35.165.250.70'}
	num=3 #total number of movies 
	totMovies=3
	numInstances=1
	instanceListFileBasename='instance_list_4455992'
		
	instanceCounter=1
	while instanceCounter <= numInstances:
		
		env.host_string='ubuntu@%s' %(instanceDict[instanceDict.keys()[instanceCounter-1]])
	        env.key_filename = '%s' %(keyPath)

		#parse encrypted keys
		i=1
		while i <= len(exec_remote_cmd('ls ~/tmp_*').split()):
		    tmpfile=exec_remote_cmd('ls ~/tmp_*').split()[i-1].split()[0] 
		    line=exec_remote_cmd('cat %s' %(tmpfile)).split()[0]
		    if len(line) <= 50:
		        r1=exec_remote_cmd('cat %s' %(tmpfile)).split()[1]
		        r1file=tmpfile
		    if len(line) >44:
		        r2=tmpfile
		    i=i+1
			
		cipher_suite = Fernet(r1)
		AWSSID=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[0])
		AWSSECRET=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[1])
		AWSACCOUNT=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[2])
		AWSREGION=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[3])

		with shell_env(AWS_ACCESS_KEY_ID=AWSSID,AWS_SECRET_ACCESS_KEY=AWSSECRET,AWS_ACCOUNT_ID=AWSACCOUNT,AWS_DEFAULT_REGION=AWSREGION):
			cp_result=exec_remote_cmd('aws s3 cp s3://%s/%s_%i.txt ~/' %(params['s3'],instanceListFileBasename,instanceCounter))
		        if cp_result.failed:
		               print 'Error: movie list copy failed.'
			print 'aws s3 cp s3://%s/%s_%i.txt ~/' %(params['s3'],instanceListFileBasename,instanceCounter)
			chmod=exec_remote_cmd('chmod +x ~/splitscript.py')
			print exec_remote_cmd('./splitscript.py %s_%i.txt %i' %(instanceListFileBasename,instanceCounter,nProcsPerInstance)
			chmod=exec_remote_cmd('chmod +x ~/downloadscript.py')
			print exec_remote_cmd('./downloadscript.py %s %s %s %s %s %s' %(AWSSID,AWSSECRET,AWSACCOUNT,AWSREGION,totMovies,'%s_%i.txt' %(instanceListFileBasename,instanceCounter)))
 	
                instanceCounter=instanceCounter+1

runThisStuff()


