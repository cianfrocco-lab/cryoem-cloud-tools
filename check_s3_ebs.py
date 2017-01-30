#!/usr/bin/env python
import os
import subprocess
from datetime import date
import datetime 

ebs_lifetime=int(subprocess.Popen('echo $EBS_LIFETIME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()) #days
s3_lifetime=int(subprocess.Popen('echo $S3_LIFETIME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

#List all S3 buckets& EBS volumes  with rln-aws
numVols=subprocess.Popen('aws ec2 describe-volumes --query "Volumes[*].{VolumeID:VolumeId}" | grep VolumeID | wc -l',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
volsToDelete=[]
vol=1
while vol <= float(numVols):
	description=subprocess.Popen('aws ec2 describe-volumes  --query "Volumes[%i].Tags[*].{Key:Key}" | grep Key' %(vol),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()
	count2=1
        while count2 <= len(description):
	        if description[count2-1] == '"Name"':
        	        value=subprocess.Popen('aws ec2 describe-volumes  --query "Volumes[%i].Tags[*].{Value:Value}" | grep Value' %(vol),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                        nameVol=value.split('"')[count2*2-1]
		count2=count2+1
	if len(nameVol.split('rln-aws-tmp-%s' %(teamname))) > 1:
		volID=subprocess.Popen('aws ec2 describe-volumes --query "Volumes[%i].{VolumeID:VolumeId}" | grep VolumeID' %(vol),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		createdDate=subprocess.Popen('aws ec2 describe-volumes --query "Volumes[%i].{CreateTime:CreateTime}"'%(vol),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split('"CreateTime":')[-1].split('"')[1]
		status=subprocess.Popen('aws ec2 describe-volumes --query "Volumes[%i].{State:State}" | grep State' %(vol),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		if status == 'available': 
			day=createdDate.split('T')[0]
			d0=date(int(day.split('-')[0]),int(day.split('-')[1]),int(day.split('-')[2]))
			d1=date(datetime.datetime.now().year,datetime.datetime.now().month, datetime.datetime.now().day)
			delta = d0 - d1
			timeDiff=delta.days-1
			if timeDiff > ebs_lifetime:
				volsToDelete.append(volID)
	vol=vol+1

for vol in volsToDelete: 

	cmd='%s/kill_volume.py %s > awslog.log' %(awsdir,vol)
        subprocess.Popen(cmd,shell=True).wait()

if os.path.exists('awslog.log'): 
	os.remove('awslog.log')

#S3 cleanup
if os.path.exists('s3.log'): 
	os.remove('s3.log')

cmd='aws s3 ls > s3.log'
subprocess.Popen(cmd,shell=True).wait()	
s3delete=[]
for line in open('s3.log','r'): 
	if len(line.split()[-1].split('rln-aws-%s' %(teamname))) > 1: 
		dates3=line.split()[0]
		year=int(dates3.split('-')[0])
		month=int(dates3.split('-')[1])
		day=int(dates3.split('-')[2])
		d0=date(year,month,day)
		d1=date(datetime.datetime.now().year,datetime.datetime.now().month, datetime.datetime.now().day)
                delta = d0 - d1
                timeDiff=delta.days
                if timeDiff > s3_lifetime:
	                s3delete.append('s3://%s' %(line.split()[-1]))

for s3 in s3delete: 
	cmd='aws s3 rb %s' %(s3)
	subprocess.Popen(cmd,shell=True).wait()


