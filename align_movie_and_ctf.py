#!/usr/bin/env python

import subprocess
import time
import sys
import os
import linecache 

movielist=sys.argv[1]
apix=sys.argv[2]
kev=sys.argv[3]
gainref=sys.argv[4]
throw=sys.argv[5]
patch=sys.argv[6]
ftbin=sys.argv[7]
doserate=sys.argv[8]
bufferMovie=sys.argv[9]
KEYID=sys.argv[10]
SECRET=sys.argv[11]
ID=sys.argv[12]
REGION=sys.argv[13]
totMovies=sys.argv[14]
instanceList=sys.argv[15]
bufferMovie=sys.argv[16]
s3=sys.argv[17]
GPUID=sys.argv[18]

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

motionCor2Path=
gctfpath=

numMovies=len(open(movielist,'r').readlines())
counter=1

if numMovies <= bufferMovie:
	bufferMovie=bufferMovie

#Start download of buffer movies
while counter <= bufferMovie:
        movietmplist=[]
        movie=linecache.getline(instanceList,counter).split()[0]
        cmd='aws s3 cp --quiet s3://%s/%s . &' %(s3,movie)
        subprocess.Popen(cmd,shell=True)
        movietmplist.append(movie)
        counter=counter+1

#Waiting script to make sure all movies are downloaded
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

#Align movies, one at a time (since this is running on a single process / GPU
counter=1
while counter <= numMovies: 
        #Next movie download
	if counter+5 > numMovies: 
		getMovie=numMovies
	movie=linecache.getline(movielist,getMovies).split()[0]
	if not os.path.exists(movie):
		cmd='aws s3 cp --quiet s3://%s/%s . &' %(s3,movie)
        	subprocess.Popen(cmd,shell=True)
	inmovie=linecache.getline(movielist,counter).split()[0]
	outmicroDW='%s_DW.mrc' %(inmovie[:-5])
	outmicro='%s.mrc' %(inmovie[:-5])
        if os.path.exists(outmicro):
        	continue
        doseinfo='-PixSize %f -kV %i' %(apix,kev)
        gainref='-Gain %s' %(gainref)
        cmd = '%s -InMrc %s -OutMrc %s -Throw %i -Iter 10 -Patch %i %i -FtBin %i -FmDose %f %s %s' %(motionCor2Path,inmovie,outmicro,throw,patch,patch,ftbin,doserate,doseinfo,gainref)
        print cmd 
	#subprocess.Popen(cmd,shell=True).wait()
	counter=counter+1
