#!/usr/bin/env python

import random
import pickle
import datetime
import shutil
import optparse
from sys import *
import os,sys,re
from optparse import OptionParser
import glob
import subprocess
from os import system
import linecache
import time
import string
from fabric.operations import run, put
from fabric.api import env,run,hide,settings
from fabric.context_managers import shell_env
from awsdatatransfer import *

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("This program will start a classroom of virtual machines on AWS")
        parser.add_option("--instance",dest="instance",type="string",metavar="Instance",default='m4.4xlarge',
                    help="Instance type on AWS (Default=t2.micro)")
	parser.add_option("--num",dest="numInstances",type="int",metavar="Number",default=1,
                    help="Number of instances (Default=1")
	parser.add_option("--ebs",dest="EBSsize",type="int",metavar="EBS",default=300,
                    help="Size of EBS volume to attach (in GB) (Default=300GB")
	parser.add_option("--cryosparc",dest="cryosparc",type="string",metavar="cryoSPARC",
                    help="Optional: Text file with cryoSPARC license numbers")
	parser.add_option("--usernamelist",dest="userlist",type="string",metavar="Users",default='',
                    help="Optional: CSV file with user name information")
	parser.add_option("--usercol",dest="usercol",type="int",metavar="Users",default='5',
                    help="Optional: CSV column number with username (Default=5)")
	parser.add_option("--pwcol",dest="pwcol",type="int",metavar="PW",default='6',
                    help="Optional: CSV column number with password (Default=6)")	
	parser.add_option("--s3bucket",dest="s3bucket",type="string",metavar="S3",default='',
                    help="Optional: S3 bucket name with USER data to be downloaded onto machines")
        parser.add_option("-d", action="store_true",dest="debug",default=False,
            help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) == 1:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#===============
def checkConflicts(params):

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','run.err')
                sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        rosettadir='%s/../rosetta/' %(awsdir)

        if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()

        if len(AWS_ID) == 0:
                print 'Error: Could not find the environmental variable $AWS_ACCOUNT_ID. Exiting'
                sys.exit()
        if len(key_ID) == 0:
                print 'Error: Could not find the environmental variable $AWS_ACCESS_KEY_ID. Exiting'
                sys.exit()
        if len(secret_ID) == 0:
                print 'Error: Could not find the environmental variable $AWS_SECRET_ACCESS_ID. Exiting'
                sys.exit()
        if len(teamname) == 0:
                print 'Error: Could not find the environmental variable $RESEARCH_GROUP_NAME. Exiting'
                sys.exit()
        if len(keypair) == 0:
                print 'Error: Could not find the environmental variable $KEYPAIR_PATH. Exiting'
                sys.exit()

        if awsregion == 'us-east-2':
                AMI='ami-fc695099'

	instance=params['instance']
        if params['debug'] is True:
                print instance
        numToRequest=10
        return awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest

#================================================
if __name__ == "__main__":

        params=setupParserOptions()

	awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest=checkConflicts(params)

	totInstances=params['numInstances']

	if params['cryosparc']: 
		totInstances=len(open(params['cryosparc'],'r').readlines())
	
	if params['userlist']: 
		usertot=len(open(params['userlist'],'r').readlines())
		if usertot != totInstances: 
			print 'User list and number of instances does not match'
			sys.exit()

	print "\n"
	print "Launching classroom of %i instances on AWS..." %(totInstances)
	print "\n"

	print "...creating storage volumes for each machine..."
	
	#Create EBS volume for tutorial
        counter=0
	timestamp=int(time.time())
        volIDlistTutorial=[]
	while counter < totInstances:

		cmd='%s/create_volume.py %i %s%s "cryoem-class-tutorialdata-%i-%i"'%(awsdir,params['EBSsize'],awsregion,'a',timestamp,counter)+'> awsebs_%i.log' %(counter)
                subprocess.Popen(cmd,shell=True).wait()

                #Get volID from logfile
                volID=linecache.getline('awsebs_%i.log' %(counter),5).split('ID: ')[-1].split()[0]
		volIDlistTutorial.append(volID)
		os.remove('awsebs_%i.log' %(counter))
		counter=counter+1

	#Create ebs volumes if user specific data
	volIDlistUser=[]
	if params['s3bucket']: 
		while counter < totInstances:

                	cmd='%s/create_volume.py %i %s%s "cryoem-class-userdata-%i-%i"'%(awsdir,params['EBSsize'],awsregion,'a',timestamp,counter)+'> awsebs_%i.log' %(counter)
	                subprocess.Popen(cmd,shell=True).wait()

        	        #Get volID from logfile
                	volID=linecache.getline('awsebs_%i.log' %(counter),5).split('ID: ')[-1].split()[0]
	                volIDlistUser.append(volID)
        	        os.remove('awsebs_%i.log' %(counter))
                	counter=counter+1

	print "...launching machines..."

       #Launch instances
        counter=0
        while counter < totInstances: 
		cmd='%s/launch_AWS_instance.py --cryosparc --tag=cryoem-class --dirname=tutorial --volume=%s --instance=%s --availZone=%sa --AMI=%s > awslog_%i.log' %(awsdir,volIDlistTutorial[counter],instance,awsregion,AMI,counter)
	        if params['debug'] is True:
        	        print cmd
	        subprocess.Popen(cmd,shell=True)
        	time.sleep(20)
		counter=counter+1

	#Wait for instance to boot up 
        instanceIDlist=[]
        instanceIPlist=[]

	counter=0
	while counter < totInstances: 
	       	isdone=0
	        qfile='awslog_%i.log' %(counter)
        	while isdone == 0:
                	r1=open(qfile,'r')
	                for line in r1:
				if len(line)>3: 
	        	                if params['debug'] is True: 
						print line
					if len(line.split()) == 2:
        	        	                if line.split()[0] == 'ID:':
                	        	                isdone=1
	                r1.close()
        	        time.sleep(10)
	        #Get IP address
        	instanceIDlist.append(subprocess.Popen('cat awslog_%i.log | grep "ID: i-"'%(counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1].strip())
	        keypair=subprocess.Popen('cat awslog_%i.log | grep ssh'%(counter), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        	instanceIPlist.append(subprocess.Popen('cat awslog_%i.log | grep ssh'%(counter), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip())
	        os.remove('awslog_%i.log' %(counter))
		counter=counter+1

	#Attach user data ebs volume (if applicable)

	if params['cryosparc']: 
		print "...activating cryoSPARC licenses..."
	
		#Read cryosparc licenses into file
		licenses=[]
		for entry in open(params['cryosparc'],'r'): 
			licenses.append(entry.split()[0])
	
		if params['debug'] is True: 
			print licenses 

		counter=0
		while counter < totInstances: 
			cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "sudo /home/EM_Packages/cryosparc/bin/cryosparc register --license-id=%s"'  %(keypair,instanceIPlist[counter],licenses[counter])
			subprocess.Popen(cmd,shell=True).wait()
	
			cfile='cryosparc.sh'
			if os.path.exists(cfile): 
				os.remove(cfile)

			c1=open(cfile,'w')
			c1.write('#!/bin/bash\n')
			c1.write('sudo /home/EM_Packages/cryosparc/bin/cryosparc start"' %(keypair,instanceIPlist[counter])
			c1.close()
			cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s cryosparc.sh ubuntu@%s:~/' %(keypair,instanceIPlist[counter])
                	subprocess.Popen(cmd,shell=True).wait()
			
			cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "bash cryosparc.sh"' %(keypair,instanceIPlist[counter])
                	subprocess.Popen(cmd,shell=True).wait()
			counter=counter+1

	print "...opening VNC clients..."

	#Start VNC & download rclone
	counter=0
	while counter < totInstances:
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "/usr/bin/wget https://downloads.rclone.org/v1.42/rclone-v1.42-linux-amd64.zip && unzip rclone-v1.42-linux-amd64.zip && /bin/rm rclone-v1.42-linux-amd64.zip"' %(keypair,instanceIPlist[counter])
		if params['debug'] is True: 
			print cmd 
		subprocess.Popen(cmd,shell=True).wait()
	
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "/usr/bin/vncserver :1"' %(keypair,instanceIPlist[counter])
		if params['debug'] is True:             
                        print cmd
		subprocess.Popen(cmd,shell=True).wait()
		counter=counter+1

	#Create login information
	print "...creating user accounts..."
	counter=0

	userlist=[]
	passwordlist=[]

	while counter < totInstances: 
		if len(params['userlist'])==0: 
			username='cryoem'
			password=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
		if len(params['userlist'])>0: 
			username=linecache.getline(params['userlist'],counter+1).split(',')[int(params['usercol'])-1]
			if username[:2] == 'um': 
				password=linecache.getline(params['userlist'],counter+1).split(',')[int(params['pwcol'])-1]
			if username[:2] != 'um': 
				password=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
		cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'sudo /usr/sbin/adduser %s --gecos "First Last,RoomNumber,WorkPhone,HomePhone" --disabled-password && sudo echo "%s:%s" | sudo chpasswd'""" %(keypair,instanceIPlist[counter],username,username,password)
		if params['debug'] is True:             
                        print cmd
		subprocess.Popen(cmd,shell=True).wait()

		userlist.append(username)
		passwordlist.append(password)

		counter=counter+1

	#sudo adduser testing --gecos "First Last,RoomNumber,WorkPhone,HomePhone" --disabled-password
  	#284  sudo echo "testing:password" | sudo chpasswd
	
	print "...starting tutorial dataset download..."

	counter=0

	#write rclone file
	rclonefile='rclone.conf'
	rcloneopen=open(rclonefile,'w')
	rcloneopen.write('[rclonename]\n')
	rcloneopen.write('type = s3\n')
	rcloneopen.write('env_auth = false\n')
	rcloneopen.write('access_key_id = %s\n' %(key_ID))
	rcloneopen.write('secret_access_key = %s\n' %(secret_ID))
	rcloneopen.write('region = %s\n' %(awsregion))
	rcloneopen.write('endpoint = \n')
	rcloneopen.write('location_constraint = %s\n' %(awsregion))
	rcloneopen.write('acl = authenticated-read\n')
	rcloneopen.write('server_side_encryption = \n')
	rcloneopen.write('storage_class = STANDARD\n')
	rcloneopen.close()

	#Tutorial transfer script
	tutfile=open('transfer.sh','w')
	tutfile.write('#!/bin/bash -x\n')
	tutfile.write('rclone-v1.42-linux-amd64/rclone copy rclonename:university-of-michigan-cryoem-workshop/ferritin_RELION2 /tutorialdata/ --transfers=20 &\n')
	tutfile.write('sudo chmod -R 755 /tutorial\n')
	tutfile.close()

	while counter<totInstances: 
		cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s rclone.conf ubuntu@%s:~/.rclone.conf > rsync.log' %(keypair,instanceIPlist[counter])
                subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s transfer.sh ubuntu@%s:~/ > rsync.log' %(keypair,instanceIPlist[counter])
                subprocess.Popen(cmd,shell=True).wait()
		
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "/bin/chmod +x transfer.sh && ./transfer.sh &"' %(keypair,instanceIPlist[counter])
		subprocess.Popen(cmd,shell=True).wait()
	
		counter=counter+1

	#Remove files
	#if os.path.exists('rclone.conf'): 
	#	os.remove('rclone.conf')
	#if os.path.exists('rsync.log'): 
	#	os.remove('rsync.log')
	#if os.path.exists('transfer.sh'): 
	#	os.remove('transfer.sh')

	print "...writing out classroom information..."

	outfilename='cryoem-class-%i-information.txt' %(timestamp)
	o1=open(outfilename,'w')
	o1.write('Information file generated for cryoem-class-%i, columns: username,IP, ID, EBS-tutorial, EBS-userdata (if applicable), CSV user info, cryosparc license #\n' %(timestamp))

	counter=0
	while counter < totInstances:

		string='%s\t%s\t%s\t%s\t' %(userlist[counter],instanceIPlist[counter],instanceIDlist[counter],volIDlistTutorial[counter])

		if params['s3bucket']: 
			string=string+'%s\t' %(volIDlistUser[counter])		

		if not params['s3bucket']: 
			string=string+'---\t'

		if len(params['userlist'])>0: 
			#Get user info
			userinfo=linecache.getline(params['userlist'],counter+1).strip()
			string=string+'%s\t'% (userinfo)
		
		if params['cryosparc']: 
			string=string+'%s\t' %(licenses[counter])
		
		o1.write('%s\n' %(string))

		counter=counter+1
	o1.close()

	#to do
	#create tutorial directory: /tutorial
	#download tutotirla data
	#download user data (if applicable) 
	#no IP address restrictions
