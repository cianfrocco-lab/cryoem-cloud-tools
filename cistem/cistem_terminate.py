#!/usr/bin/env python

import pickle
import subprocess
import os
import sys 

if not os.path.exists('.instanceIDlist.txt'): 
	print '\nCannot terminate instance - could not find file .instanceIDlist.txt. Did you launch cisTEM on AWS from this directory?\n'
	sys.exit()
if not os.path.exists('.instanceIPlist.txt'):
        print '\nCannot terminate instance - could not find file .instanceIPlist.txt. Did you launch cisTEM on AWS from this directory?\n'
        sys.exit()

#Get AWS dir
awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]

#Read in pickle files
with open ('.instanceIDlist.txt', 'rb') as fp:
                instanceIDlist = pickle.load(fp)
with open ('.instanceIPlist.txt', 'rb') as fp:
                instanceIPlist = pickle.load(fp)

print '\nTerminating instance %s...\n' %(instanceIDlist[0])

cmd='%s/../aws/kill_instance.py %s' %(awsdir,instanceIDlist[0])
subprocess.Popen(cmd,shell=True).wait()

os.remove('.instanceIDlist.txt')
os.remove('.instanceIPlist.txt')
