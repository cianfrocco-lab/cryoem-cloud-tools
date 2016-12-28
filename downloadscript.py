#!/usr/bin/env python
import os
import subprocess
import linecache
import sys
import time
KEYID=sys.argv[1]
SECRET=sys.argv[2]
ID=sys.argv[3]
REGION=sys.argv[4]
totMovies=sys.argv[5]
instanceList=sys.argv[6]
bufferMovie=sys.argv[7]
s3=sys.argv[8]

cmd='#!/bin/sh\n'
cmd+="export AWS_ACCESS_KEY_ID=%s\n"%(KEYID)
cmd+="export AWS_SECRET_ACCESS_KEY=%s\n" %(SECRET)
cmd+="export AWS_ACCOUNT_ID=%s\n"%(ID)
cmd+="export AWS_DEFAULT_REGION=%s\n"%(REGION)

o1=open('aws_init.sh','w')
o1.write(cmd)
o1.close()

cmd2="source aws_init.sh > init.txt"
subprocess.Popen(cmd2,shell=True).wait()

os.remove("init.txt")

counter=1

if float(bufferMovie) > float(totMovies):
	bufferMovie=float(totMovies)

#Startdownload of buffer movies 
while counter <= float(bufferMovie):

        midcounter=0
        movietmplist=[]
        while midcounter < float(bufferMovie):

                movie=linecache.getline(instanceList,counter+midcounter).split()[0]
                cmd='aws s3 cp --quiet s3://%s/%s . &' %(s3,movie)
                subprocess.Popen(cmd,shell=True)
                movietmplist.append(movie)
                midcounter=midcounter+1
        for movietmp in movietmplist:
                if not os.path.exists(movietmp):
                        time.sleep(10)
                filesize=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
                time.sleep(10)
                filesize2=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
                if filesize == filesize2:
                        continue
                flag=0
                while flag !=1:
                        filesize=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
                        time.sleep(5)
                        filesize2=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
                        if filesize == filesize2:
                                flag=1
                        time.sleep(5)
                continue

#Pick up where left off
while counter <= float(totMovies):

	midcounter=0
	movietmplist=[]
	while midcounter < float(bufferMovie):

		movie=linecache.getline(instanceList,counter+midcounter).split()[0]
		cmd='aws s3 cp --quiet s3://%s/%s . &' %(s3,movie)
		subprocess.Popen(cmd,shell=True)	
		movietmplist.append(movie)
		midcounter=midcounter+1
	for movietmp in movietmplist:
		if not os.path.exists(movietmp):
			time.sleep(10)
		filesize=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])	
		time.sleep(10)
		filesize2=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])	
		if filesize == filesize2: 
			continue
		flag=0
		while flag !=1: 
			filesize=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
			time.sleep(5)
	                filesize2=float(subprocess.Popen('wc -c %s' %(movietmp),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])
			if filesize == filesize2: 
				flag=1
			time.sleep(5)
		continue

	#Wait to continue until group is aligned 
	for movietmp in movietmplist:
                waitflag=0
		while waitflag != 1: 
			if os.path.exists('%s_ctfinfo.txt' %(movietmp.split('.mrc')[0])):
				waitflag=1
			print 'waiting for %s to be ctf estimated' %(movietmp)
			
			if not os.path.exists('%s_ctfinfo.txt' %(movietmp.split('.mrc')[0])):
				time.sleep(20)
                continue
	

	counter=counter+midcounter
