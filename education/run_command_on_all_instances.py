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
        parser.add_option("--instancelist",dest="instancelist",type="string",metavar="InstanceList",
                    help="AWS instance list file generated from launch_classroom.py")
        parser.add_option("--command",dest="command",type="string",metavar="Command",
                    help="Text file with commands to run on each instance, where each line is a different command")
	parser.add_option("--cryosparc",dest="cryosparc",type="string",metavar="cryoSPARC",
                    help="Optional: Provide cryoSPARC license file to activate cryoSPARC instances")
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

#================================================
if __name__ == "__main__":

        params=setupParserOptions()
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	instanceIPlist=[]
	userlist=[]
	passwordlist=[]
	for line in open(params['instancelist'],'r'):
                if 'Information' in line:
                        continue
                instanceIPlist.append(line.split()[2])
		userlist.append(line.split()[0])
		passwordlist.append(line.split()[1]
)
	if params['cryosparc']: 
		#Read cryosparc licenses into file
                licenses=[]
                for entry in open(params['cryosparc'],'r'):
                        licenses.append(entry.split()[0])

	cmdlist=[]
	for line in open(params['command'],'r'):
                cmdlist.append(line.strip())	
        counter=0
	
        while counter<len(instanceIPlist):

                for cmdrun in cmdlist: 
			cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "%s"' %(keypair,instanceIPlist[counter],cmdrun)
			if params['debug'] is True:
        	                print cmd
	                subprocess.Popen(cmd,shell=True).wait()

		if params['cryosparc']: 
			if os.path.exists('config.sh'): 
				os.remove('config.sh')

			configopen=open('config.sh','w')
			configopen.write('\n')
			configopen.write('export CRYOSPARC_LICENSE_ID="%s"\n')
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

			cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s "source ~/.bashrc && /home/ubuntu/cryosparc2_master/bin/cryosparcm start && /home/ubuntu/cryosparc2_master/bin/cryosparcm createuser %s@umich.edu %s && cd /home/ubuntu/cryosparc2_worker && /home/ubuntu/cryosparc2_worker/bin/cryosparcw connect localhost localhost 39000 --sshstr ubuntu@localhost"' %(keypair,instanceIPlist[counter],userlist[counter],passwordlist[counter])
                        if params['debug'] is True:
                                print cmd
                        subprocess.Popen(cmd,shell=True).wait()


		counter=counter+1

