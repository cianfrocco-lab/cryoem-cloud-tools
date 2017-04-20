#!/usr/bin/env python

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

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("This program will wait for a rosetta refinement to finish on AWS.")
        parser.add_option("--instanceIDlist",dest="instanceID",type="string",metavar="FILE",
                    help="Instance ID list (pickle dump)")
        parser.add_option("--instanceIPlist",dest="instanceIP",type="string",metavar="FILE",
                    help="Instance IP list (pickle dump)")
        parser.add_option("--volIDlist",dest="volID",type="string",metavar="FILE",
                    help="Volume ID list (pickle dump)")
        parser.add_option("--numModels",dest="numModels",type="int",metavar="INT",
                    help="Total number of models in rosetta run")
	parser.add_option("--numPerInstance",dest="numPerInstance",type="int",metavar="Number",
                    help="Number of models per instance requested")
	parser.add_option("--outdir",dest='outdir',type="string",metavar='FILE',
		    help='Output directory')
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))
        if len(sys.argv) <= 2:
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
        startTime=datetime.datetime.utcnow()
	startday=now.day
        starthr=now.hour
        startmin=now.minute

        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	time.sleep(60)
	loadMin=5
	#Read in pickle files
	with open (params['instanceIP'], 'rb') as fp:
		instanceIPlist = pickle.load(fp)
	with open (params['volID'], 'rb') as fp:
                volIDlist = pickle.load(fp)
	with open (params['instanceID'], 'rb') as fp:
                instanceIDlist = pickle.load(fp)

	l='%s/rosetta.out' %(params['outdir'])

	cmd="echo 'Starting to check status of Rosetta refinement at %sUTC' >> %s" %(startTime.strftime('%Y-%m-%dT%H:%M:00'),l)
	subprocess.Popen(cmd,shell=True).wait()

	os.makedirs('%s/output' %(params['outdir']))

	counter=0
	instanceCounter=1
	while counter < len(instanceIPlist):
	        isdone=0
        	while isdone == 0:
                	#If cloudwatch has load < 5% BUT there aren't finished PDBs yet, job crashed. Terminate.
	                currentTime=datetime.datetime.utcnow()
        	        if os.path.exists('%s/cloudwatchtmp.log'%(params['outdir'])):
                	        os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
	                cmd='aws cloudwatch get-metric-statistics --metric-name CPUUtilization --start-time %s  --period 300 --namespace AWS/EC2 --statistics Average --dimensions Name=InstanceId,Value=%s --end-time %s > %s/cloudwatchtmp.log' %(startTime.strftime('%Y-%m-%dT%H:%M:00'),instanceIDlist[counter],currentTime.strftime('%Y-%m-%dT%H:%M:00'),params['outdir'])
        	        subprocess.Popen(cmd,shell=True).wait()
                	o1=open('%s/cloudwatchtmp.log'%(params['outdir']),'r')
	                for line in o1:
        	                if len(line.split())>0:
                	                if line.split()[0] == '"Average":':
                        	                load=float(line.split()[1][:-1])
                                	        cmd="echo 'Current load on instance %i is %f at %sUTC' >> %s" %(counter+1,load,currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
                                                subprocess.Popen(cmd,shell=True).wait()
						if load < loadMin:
							#Download all pdb files, take note if you didn't download enough files consdiering number of models requested
	                                                isdone=1
							cmd='echo "--------> Instance %i finished at %sUTC" >> %s' %(counter+1,currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
							subprocess.Popen(cmd,shell=True).wait()
        						currCounter=1				
							while currCounter <= params['numPerInstance']:
								cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/S_%i_0001.pdb %s/output/S_%i_0001.pdb' %(keypair,instanceIPlist[counter],currCounter,params['outdir'],instanceCounter)
								subprocess.Popen(cmd,shell=True).wait()		

								cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/score_%i.sc %s/output/S_%i_0001_score.sc' %(keypair,instanceIPlist[counter],currCounter,params['outdir'],instanceCounter)
                                                                subprocess.Popen(cmd,shell=True).wait()
								instanceCounter=instanceCounter+1
								currCounter=currCounter+1	

							cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceIDlist[counter],params['outdir'])
        						subprocess.Popen(cmd,shell=True).wait()

		        o1.close()
                	os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
	                time.sleep(60)
		counter=counter+1

        cmd='echo "Rosetta refinement finished. Shutting down instances %s" >> %s' %(currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
	subprocess.Popen(cmd,shell=True).wait()

	counter=0
	while counter < len(instanceIPlist):
        	isdone=0
        	while isdone == 0:
              		status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceIDlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
              		if status == 'terminated':
                    		isdone=1
              	time.sleep(10)

        	cmd='aws ec2 delete-volume --volume-id %s > %s/tmp4949585940.txt' %(volIDlist[counter],params['outdir'])
        	subprocess.Popen(cmd,shell=True).wait()
		counter=counter+1

        #now=datetime.datetime.now()
        #finday=now.day
        #finhr=now.hour
        #finmin=now.minute
        #if finday != startday:
        #        finhr=finhr+24
        #deltaHr=finhr-starthr
        #if finmin > startmin:
        #        deltaHr=deltaHr+1


