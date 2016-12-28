#!/usr/bin/env python

import linecache
import sys
import subprocess

KEYID=sys.argv[1]
SECRET=sys.argv[2]
ID=sys.argv[3]
REGION=sys.argv[4]
totMovies=sys.argv[5]
instanceList=sys.argv[6]

subprocess.Popen("export AWS_ACCESS_KEY_ID=%s" %(KEYID),shell=True, stdout=subprocess.PIPE)
subprocess.Popen("export AWS_SECRET_ACCESS_KEY=%s" %(SECRET),shell=True, stdout=subprocess.PIPE)
subprocess.Popen("export AWS_ACCOUNT_ID=%s" %(ID),shell=True, stdout=subprocess.PIPE)
subprocess.Popen("export AWS_DEFAULT_REGION=%s" %(REGION),shell=True, stdout=subprocess.PIPE)
counter=1
while counter <= totMovies: 
	movie=linecache.getline(instanceList,counter)
        print movie
        counter=counter+1

