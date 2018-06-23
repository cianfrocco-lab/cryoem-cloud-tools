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
	parser.add_option("--ebs",dest="EBSsize",type="int",metavar="EBS",default=3000,
                    help="Size of EBS volume to attach for tutorial data (in GB) (Default=3000GB")
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

#====================
def module_exists(module_name):
        try:
                __import__(module_name)
        except ImportError:
                return False
        else:
                return True

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
                AMI='ami-31261f54'

	instance=params['instance']
        if params['debug'] is True:
                print instance
        numToRequest=10
        return awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest,

#================================================
if __name__ == "__main__":

        params=setupParserOptions()

	awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,AMI,instance,numToRequest=checkConflicts(params)

	totInstances=params['numInstances']

	if params['cryosparc']: 
		totInstances=len(open(params['cryosparc'],'r').readlines())
	
	if params['userlist']: 
		usertot=len(open(params['userlist'],'r').readlines())
		if params['cryosparc']: 
			if usertot != totInstances: 
				print 'User list and number of instances does not match'
				sys.exit()
		totInstances=usertot

	print "\n"
	print "Launching classroom of %i instances on AWS..." %(totInstances)
	print "\n"

	print "...launching machines..."

       #Launch instances
        counter=0
        while counter < totInstances: 
		cmd='%s/launch_AWS_instance.py --noSSHlimit --alwaysOn --cryosparc --tag=cryoem-class --noEBS --instance=%s --AMI=%s > awslog_%i.log' %(awsdir,instance,AMI,counter)
	        if params['debug'] is True:
        	        print cmd
	        subprocess.Popen(cmd,shell=True)
        	time.sleep(20)
		counter=counter+1

	#Wait for instance to boot up 
        instanceIDlist=[]
        instanceIPlist=[]
	dnslist=[]
	azlist=[]

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
		dnslist.append(subprocess.Popen("aws ec2 describe-instances  --instance-id=%s --query 'Reservations[*].Instances[*].NetworkInterfaces[*].Association.{PubAddress:PublicDnsName}' | grep PubAddress" %(instanceIDlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split('"')[-2])
		azlist.append(subprocess.Popen('cat awslog_%i.log | grep AvailabilityZoneInfo' %(counter), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-1].strip())
	        os.remove('awslog_%i.log' %(counter))
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

                #cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'sudo su -c "cd ~/ && /usr/bin/vncserver :1" %s'""" %(keypair,instanceIPlist[counter],username)
                #if params['debug'] is True:
                #        print cmd
                #subprocess.Popen(cmd,shell=True).wait()        

                #cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'sudo su -c "cd ~/ && /usr/bin/wget https://downloads.rclone.org/v1.42/rclone-v1.42-linux-amd64.zip && unzip rclone-v1.42-linux-amd64.zip && /bin/rm rclone-v1.42-linux-amd64.zip" %s'""" %(keypair,instanceIPlist[counter],username)
                #if params['debug'] is True:
                #        print cmd
                #subprocess.Popen(cmd,shell=True).wait()

                cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'sudo su -c "cd ~/ && cp ~/../ubuntu/.bashrc ~/" %s'""" %(keypair,instanceIPlist[counter],username)
                if params['debug'] is True:
                        print cmd
                subprocess.Popen(cmd,shell=True).wait()

                userlist.append(username)
                passwordlist.append(password)

                counter=counter+1
	print "...creating storage volumes for each machine..."
	#Attach user data ebs volume (if applicable)
	#Create EBS volume for tutorial
        counter=0
        timestamp=int(time.time())
        volIDlistTutorial=[]
	ebstutorialsize=[]
        while counter < totInstances:

		if os.path.exists('awsebs_%i.log' %(counter)): 
			os.remove('awsebs_%i.log' %(counter))

                cmd='%s/create_volume.py %i %s "cryoem-class-tutorialdata-%i-%i"'%(awsdir,params['EBSsize'],azlist[counter],timestamp,counter)+'> awsebs_%i.log' %(counter)
                ebstutorialsize.append(params['EBSsize'])
		if params['debug'] is True: 
			print cmd 
		subprocess.Popen(cmd,shell=True).wait()

                #Get volID from logfile
                volID=linecache.getline('awsebs_%i.log' %(counter),5).split('ID: ')[-1].split()[0]
                if params['debug'] is True: 
			print volID
		volIDlistTutorial.append(volID)
                os.remove('awsebs_%i.log' %(counter))

		time.sleep(5)
		#Wait for available
		isdone=0
		while isdone==0: 
			checkavail=subprocess.Popen('aws ec2 describe-volumes --volume-ids %s | grep State' %(volID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
			if checkavail.split()[-1].split('"')[1] == 'available': 
				isdone=1
			time.sleep(1)

		if params['debug'] is True: 
			print 'aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdf > tmp3re3333.log' %(volID,instanceIDlist[counter])
		volID=subprocess.Popen('aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdf > tmp3re3333.log' %(volID,instanceIDlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()

		time.sleep(3)
		if os.path.exists('tmp3re3333.log'):
        		os.remove('tmp3re3333.log')
   		time.sleep(10)
   		env.host_string='ubuntu@%s' %(instanceIPlist[counter])
   		env.key_filename = '%s' %(keypair)
   		dir_exists=exec_remote_cmd('ls /tutorial')
   		if len(dir_exists.split()) >0:
        		if dir_exists.split()[2] == 'access':
           			mk=exec_remote_cmd('sudo mkdir /tutorial/')
   		check_NFS=exec_remote_cmd('sudo file -s /dev/xvdf')
	   	if 'filesystem' not in check_NFS:
        		nfsmount=exec_remote_cmd('sudo mkfs -t ext4 /dev/xvdf')
	 	  	mount_out=exec_remote_cmd('sudo mount /dev/xvdf /tutorial')
   			chmod=exec_remote_cmd('sudo chmod 777 /tutorial/')
		if 'filesystem' not in check_NFS:
        		chmod=exec_remote_cmd('rm -rf /tutorial/lost+found')

                counter=counter+1
	counter=0
        #Create ebs volumes if user specific data
        volIDlistUser=[]
	ebsusersize=[]
        if params['s3bucket']:
                while counter < totInstances:
			#Get size of directory on AWS
			print 'aws s3 ls --summarize --recursive s3://%s/%s | grep "Total Size"' %(params['s3bucket'],userlist[counter])
			print subprocess.Popen('aws s3 ls --summarize --recursive s3://%s/%s | grep "Total Size"' %(params['s3bucket'],userlist[counter]), shell=True, stdout=subprocess.PIPE).stdout.read()
			s3sizecheck=subprocess.Popen('aws s3 ls --summarize --recursive s3://%s/%s | grep "Total Size"' %(params['s3bucket'],userlist[counter]), shell=True, stdout=subprocess.PIPE).stdout.read()
			if len(s3sizecheck.split())>1: 
				s3size=subprocess.Popen('aws s3 ls --summarize --recursive s3://%s/%s | grep "Total Size"' %(params['s3bucket'],userlist[counter]), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-1]
			if len(s3sizecheck.split())==1: 
				s3size=0
			if params['debug'] is True: 
				print '%s = %s' %(userlist[counter],s3size)
			s3size=float(s3size)*4
			if s3size > 5000000000000: #Limit: 5 TB 
				s3size=5000000000000
			if s3size < 800000000000: 
				s3size=1000000000000
                        if os.path.exists('awsebs%i.log' %(counter)): 
				os.remove('awsebs%i.log' %(counter))
			cmd='%s/create_volume.py %i %s "cryoem-class-userdata-%i-%i"'%(awsdir,int(round(s3size/1000000000)),azlist[counter],timestamp,counter)+'> awsebs%i.log' %(counter)
                        ebsusersize.append(s3size/1000000000)
			if params['debug'] is True: 
				print cmd 
			subprocess.Popen(cmd,shell=True).wait()

                        #Get volID from logfile
			if params['debug'] is True: 
				print linecache.getline('awsebs%i.log' %(counter),5)
                        volID=linecache.getline('awsebs%i.log' %(counter),5).split('ID: ')[-1].split()[0]
                        if params['debug'] is True: 
				print volID
			volIDlistUser.append(volID)
                        os.remove('awsebs%i.log' %(counter))
	
			time.sleep(5)
                	#Wait for available
                	isdone=0
                	while isdone==0: 
                        	checkavail=subprocess.Popen('aws ec2 describe-volumes --volume-ids %s | grep State' %(volID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                        	if checkavail.split()[-1].split('"')[1] == 'available': 
                	                isdone=1
        	                time.sleep(1)
	
			time.sleep(10)
	
			if params['debug'] is True: 
				print 'aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdh > tmp3re3333.log' %(volID,instanceIDlist[counter])
			volID=subprocess.Popen('aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdh > tmp3re3333.log' %(volID,instanceIDlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()

	                time.sleep(3)
        	        if os.path.exists('tmp3re3333.log'):
                	        os.remove('tmp3re3333.log')
	                time.sleep(10)
        	        env.host_string='ubuntu@%s' %(instanceIPlist[counter])
                	env.key_filename = '%s' %(keypair)
	                dir_exists=exec_remote_cmd('ls /userdata')
        	        if len(dir_exists.split()) >0:
                	        if dir_exists.split()[2] == 'access':
                        	        mk=exec_remote_cmd('sudo mkdir /userdata/')
	                check_NFS=exec_remote_cmd('sudo file -s /dev/xvdh')
        	        if 'filesystem' not in check_NFS:
                	        nfsmount=exec_remote_cmd('sudo mkfs -t ext4 /dev/xvdh')
                        	mount_out=exec_remote_cmd('sudo mount /dev/xvdh /userdata')
	                        chmod=exec_remote_cmd('sudo chmod 777 /userdata/')
        	        if 'filesystem' not in check_NFS:
                	        chmod=exec_remote_cmd('rm -rf /userdata/lost+found')
			chmod=exec_remote_cmd('sudo mkdir /userdata/cryosparc_scratch')
			chmod=exec_remote_cmd('sudo chmod 777 /userdata/cryosparc_scratch')

                        counter=counter+1

	if params['cryosparc']: 
		print "...activating cryoSPARC licenses..."
	
		#Read cryosparc licenses into file
		licenses=[]
		for entry in open(params['cryosparc'],'r'): 
			licenses.append(entry.split()[1])
	
		if params['debug'] is True: 
			print licenses 

		counter=0
		while counter < totInstances: 

			fabric_test=module_exists('fabric.api')
			if fabric_test is False:
		        	print 'Error: Could not find fabric installed and it is required. Install from here: http://www.fabfile.org/installing.html'
			        sys.exit()
			#Import Fabric modules now: 
			from fabric.operations import run, put
			from fabric.api import env,run,hide,settings
			from fabric.context_managers import shell_env
			from fabric.operations import put

			#List instances given a users tag
   			env.host_string='ubuntu@%s' %(instanceIPlist[counter])
   			env.key_filename = '%s' %(keypair)
			#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc/bin/cryosparc:$PATH; /home/ubuntu/cryosparc/bin/cryosparc register --license-id=%s' %(licenses[counter]))
		   	#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc/bin/cryosparc:$PATH; /home/ubuntu/cryosparc/bin/cryosparc start')
			#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc/bin/cryosparc:$PATH; /home/ubuntu/cryosparc/bin/cryosparc stop')
			#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc/bin/cryosparc:$PATH; /home/ubuntu/cryosparc/bin/cryosparc start')
			#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc2_master/bin; /home/ubuntu/cryosparc2_master/bin/cryosparcm start')
			#exportpath=exec_remote_cmd('export PATH=/home/ubuntu/cryosparc2_master/bin; /home/ubuntu/cryosparc2_master/bin/cryosparcm createuser %s %s' %(userlist[counter],passwordlist[counter]))
			#cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "source ~/.bashrc && /home/ubuntu/cryosparc2_master/bin/cryosparcm start && /home/ubuntu/cryosparc2_master/bin/cryosparcm createuser %s@umich.edu %s && cd /home/ubuntu/cryosparc2_worker && /home/ubuntu/cryosparc2_master/bin/cryosparcw connect localhost localhost 39000 --sshstr ubuntu@localhost"' %(keypair,instanceIPlist[counter],userlist[counter],passwordlist[counter])
			#if params['debug'] is True: 
			#	print cmd 
			#subprocess.Popen(cmd,shell=True).wait()
			
			if os.path.exists('config.sh'): 
				os.remove('config.sh')

			configopen=open('config.sh','w')
			configopen.write('\n')
			configopen.write('export CRYOSPARC_LICENSE_ID="%s"\n' %(licenses[counter]))
			configopen.write('export CRYOSPARC_DB_PATH="/home/ubuntu/cryosparc2_db"\n')
			configopen.write('export CRYOSPARC_BASE_PORT=39000\n')
			configopen.write('export CRYOSPARC_DEVELOP=false\n')
			configopen.write('export CRYOSPARC_INSECURE=false\n')
			configopen.close()

			cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "rm /home/ubuntu/cryosparc2_master/config.sh" """ %(keypair,instanceIPlist[counter])
			if params['debug'] is True:
                                print cmd
                        subprocess.Popen(cmd,shell=True).wait()


			cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s config.sh ubuntu@%s:~/cryosparc2_master/' %(keypair,instanceIPlist[counter])
			if params['debug'] is True: 
				print cmd
	                subprocess.Popen(cmd,shell=True).wait()

			cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'source ~/.bashrc && /home/ubuntu/cryosparc2_master/bin/cryosparcm start && /home/ubuntu/cryosparc2_master/bin/cryosparcm createuser %s@umich.edu "%s" && cd /home/ubuntu/cryosparc2_worker && /home/ubuntu/cryosparc2_worker/bin/cryosparcw connect localhost localhost 39000 --sshstr ubuntu@localhost'""" %(keypair,instanceIPlist[counter],userlist[counter],passwordlist[counter])
                        if params['debug'] is True:
                                print cmd
                        subprocess.Popen(cmd,shell=True).wait()


			counter=counter+1

	print "...opening VNC clients..."

	counter=0
	while counter < totInstances: 
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "source ~/.bashrc && sudo mkdir ../%s/.vnc/ &&  sudo cp .vnc/passwd ../%s/.vnc/ && sudo chown -R %s /home/%s/.vnc/"' %(keypair,instanceIPlist[counter],userlist[counter],userlist[counter],userlist[counter],userlist[counter])
		if params['debug'] is True:
                	print cmd
                subprocess.Popen(cmd,shell=True).wait()

		cmd="""ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s 'sudo su -c "cd ~/ && /usr/bin/vncserver :1 -geometry 1440x900" %s'""" %(keypair,instanceIPlist[counter],userlist[counter])
                if params['debug'] is True:
                        print cmd
                subprocess.Popen(cmd,shell=True).wait() 

		counter=counter+1

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
	rcloneopen.write('[rclonedata]\n')
        rcloneopen.write('type = s3\n')
        rcloneopen.write('env_auth = false\n')
        rcloneopen.write('access_key_id = %s\n' %(key_ID))
        rcloneopen.write('secret_access_key = %s\n' %(secret_ID))
        rcloneopen.write('region = us-east-1\n') #Hard coded
        rcloneopen.write('endpoint = \n')
        rcloneopen.write('location_constraint = us-east-1\n')
        rcloneopen.write('acl = authenticated-read\n')
        rcloneopen.write('server_side_encryption = \n')
        rcloneopen.write('storage_class = STANDARD\n')
	rcloneopen.close()


	while counter<totInstances: 

		#Tutorial transfer script
		if os.path.exists('transfer.sh'): 
			os.remove('transfer.sh')
	        tutfile=open('transfer.sh','w')
        	tutfile.write('#!/bin/bash -x\n')
	        tutfile.write('sudo chmod 777 /tutorial\n')
		tutfile.write('sudo su -c "cd ~/ && wget https://downloads.rclone.org/v1.42/rclone-v1.42-linux-amd64.zip && unzip rclone-v1.42-linux-amd64.zip" %s\n' %(userlist[counter]))
        	tutfile.write('sudo su -c "cp ~/../ubuntu/.rclone.conf ~/.rclone.conf && ~/rclone-v1.42-linux-amd64/rclone copy rclonename:university-of-michigan-cryoem-workshop/ /tutorial/ --transfers=20" %s\n' %(userlist[counter]))
		if params['s3bucket'] and params['userlist']: 
			tutfile.write('sudo su -c "~/rclone-v1.42-linux-amd64/rclone copy rclonedata:%s/%s /userdata/ --transfers=20" %s\n' %(params['s3bucket'],userlist[counter],userlist[counter]))
		tutfile.write('sudo su -c "rm ~/.rclone.conf" %s\n' %(userlist[counter]))
		tutfile.write('rm ~/.rclone.conf\n')
	        tutfile.close()

		cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s rclone.conf ubuntu@%s:~/.rclone.conf > rsync.log' %(keypair,instanceIPlist[counter])
                subprocess.Popen(cmd,shell=True).wait()

		cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s transfer.sh ubuntu@%s:~/ > rsync.log' %(keypair,instanceIPlist[counter])
                subprocess.Popen(cmd,shell=True).wait()
		
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "/bin/chmod +x transfer.sh && ./transfer.sh"&' %(keypair,instanceIPlist[counter])
		if params['debug'] is True: 
			print cmd 
		subprocess.Popen(cmd,shell=True).wait()
		counter=counter+1

	#Remove files
	if params['debug'] is False: 
		if os.path.exists('rclone.conf'): 
			os.remove('rclone.conf')
		if os.path.exists('rsync.log'): 
			os.remove('rsync.log')
		if os.path.exists('transfer.sh'): 
			os.remove('transfer.sh')

	print "...writing out classroom information..."

	outfilename='cryoem-class-%i-information.txt' %(timestamp)
	o1=open(outfilename,'w')
	o1.write('Information file generated for cryoem-class-%i, columns: username, passwd, IP, ID, AZ, EBS-tutorial, EBS-userdata (if applicable), CSV user info, cryosparc license #\n' %(timestamp))
	counter=0
	while counter < totInstances:

		userinfoline=linecache.getline(params['userlist'],counter+1)

		o2=open('%s_AWS_info.txt' %(userinfoline.split(',')[1]),'w')		

		string='%s\t%s\t%s\t%s\t%s\t%s\t' %(userlist[counter],passwordlist[counter],instanceIPlist[counter],instanceIDlist[counter],azlist[counter],volIDlistTutorial[counter])

		string2='Participant: %s, %s\n' %(userinfoline.split(',')[1],userinfoline.split(',')[0])
		string2+='To log onto AWS: ssh -Y %s@%s\n' %(userlist[counter],instanceIPlist[counter])
		if 'um' in userlist[counter]: 
			string2+='--> use password provided for access UMich wifi\n\n'
		if 'um' not in userlist[counter]:
			string2+='Password: %s\n' %(passwordlist[counter])
		string2+='To log onto AWS, allowing remote desktop with VNC: ssh -Y -L 5901:localhost:5901 %s@%s\n' %(userlist[counter],instanceIPlist[counter])
		string2+='\nTransferring data:\n'
		string2+='To transfer TO AWS: scp file.txt %s@%s:/path/to/directory/\n' %(userlist[counter],instanceIPlist[counter])
		string2+='To transfer FROM AWS: scp %s@%s:/path/to/file.txt .\n' %(userlist[counter],instanceIPlist[counter])
		string2+='\nTutorial data location: /tutorial\n'
		string2+='--> See read me document: /tutorial/Tutorial_data_README.txt for more information\n'
		string2+='\nUser data location: /userdata\n'
		string2+='\ncryoSPARC running information:\n'
		string2+='Web address = %s:39000\n' %(dnslist[counter])
		string2+='Username: %s@umich.edu\n' %(userlist[counter])
		if 'um' in userlist[counter]:
                        string2+='--> use password provided for access UMich wifi\n\n'
                if 'um' not in userlist[counter]:
                        string2+='Password: %s\n' %(passwordlist[counter])
		string2+='\nRELION job running information:\n'
		string2+='To use all GPUs:\n'
		string2+='GPU=0,1,2,3\n'
		string2+='MPI=5\n'
		string2+='threads=8\n'
		string2+='\nComputing information for AWS machine:\n'
		string2+='GPUs = 4 x NVIDIA Tesla M60 (8GB RAM/GPU)\n'
		string2+='CPUs = 64\n'
		string2+='RAM = 488 GB\n'
		string2+='Name of machine type on AWS= g3.16xlarge\n'
		string2+='Cost per hour = $4.56\n\n\n\n'
		o2.write(string2)

		o2.close()

		string=string+'%s\t' %(ebstutorialsize[counter])

		if params['s3bucket']: 
			string=string+'%s\t' %(volIDlistUser[counter])		
			string=string+'%s\t' %(ebsusersize[counter])
		if not params['s3bucket']: 
			string=string+'---\t'
			string=string+'---\t'

		if len(params['userlist'])>0: 
			#Get user info
			userinfo=linecache.getline(params['userlist'],counter+1).strip()
			string=string+'%s\t'% (userinfo)
		
		if params['cryosparc']: 
			string=string+'%s\t%s\t' %(licenses[counter],dnslist[counter])
		
		o1.write('%s\n' %(string))

		counter=counter+1
	o1.close()

	#to do
	#cryosparc 
	#download user data (if applicable) 
