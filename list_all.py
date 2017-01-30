#!/usr/bin/env python

import subprocess
import os
import sys 

if len(sys.argv) ==1:
        print '\nUsage: awsls_admin [region]\n'
        print '\nSpecify region (NOT availability zone) that will be displayed for all users\n'
        sys.exit()

region=sys.argv[1]

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

#Get number of instances to loop over
numInstances=subprocess.Popen('aws ec2 describe-instances --region %s --query "Reservations[*].Instances[*].{InstanceID:InstanceId}" | grep InstanceID | wc -l' %(region),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0
print '\nAWS usage in region %s' %(region)

print '\n---------------------------------------------------------------------------------------------'
print 'ReservedInstanceType\tAvail. Zone\tInstanceID\tStatus\t\tIP Address\tUser'
print '---------------------------------------------------------------------------------------------'

if float(numInstances) == 0:
	print 'No instances found\n'

while counter < float(numInstances): 
	instanceID=subprocess.Popen('aws ec2 describe-instances --region %s  --query "Reservations[%i].Instances[*].{InstanceID:InstanceId}" | grep InstanceID' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	if len(instanceID) > 0:
		instanceID=instanceID.split()[-1].split('"')[1]
	if len(instanceID) == 0:
		instanceID='---'
	status=subprocess.Popen('aws ec2 describe-instances --region %s --query "Reservations[%i].Instances[*].{State:State}" | grep Name' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	if len(status) > 0: 
		status=status.split()[-1].split('"')[1]
	if len(status) == 0: 
		status='--'
	
	owner=subprocess.Popen('aws ec2 describe-instances --region %s --query "Reservations[%i].Instances[*].{Owner:KeyName}" | grep Owner' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	instanceType=subprocess.Popen('aws ec2 describe-instances --region %s --query "Reservations[%i].Instances[*].{Type:InstanceType}" | grep Type' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-instances  --region %s --query "Reservations[%i].Instances[*]" | grep AvailabilityZone' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	PublicIP=subprocess.Popen('aws ec2 describe-instances --region %s --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(region,instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	
	if len(PublicIP) > 0:
		
		if PublicIP[0] == '"':
			PublicIP=PublicIP.split()[-1].split('"')
			if len(PublicIP)>1:
				PublicIP='\t%s'%(PublicIP[1])
			if len(PublicIP)==1:
				PublicIP=PublicIP[0]
				if PublicIP == 'null':
					PublicIP='---\t'
	if len(PublicIP) == 0:
		PublicIP='---'
	
	print '%s\t\t%s\t%s\t%s\t%s\t%s' %(instanceType,availZone,instanceID,status,PublicIP,owner)

	counter=counter+1

#Info needed: instance ID, AMI, region, zone, tag
numSpotInstances=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s  --query "SpotInstanceRequests[*].{State:State}"|grep State | wc -l' %(region),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\n----------------------------------------------------------------------------------------------------------------------------------------'
print 'SpotInstanceType\tAvail. Zone\tSpotInstanceID\tSpotStatus\tInstanceID\tStatus\t\tIP Address\tPrice\tUser\t'
print '----------------------------------------------------------------------------------------------------------------------------------------'

if float(numSpotInstances) == 0:
        print 'No spot instances found\n'

while counter < float(numSpotInstances):
	instanceID='---\t'
	status='---\t'
	PublicIP='---\t'
	spotID=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s  --query "SpotInstanceRequests[%i].{SpotID:SpotInstanceRequestId}"|grep SpotID' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	spotStatus=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s --query "SpotInstanceRequests[%i].{State:State}"|grep State' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	instanceType=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s  --query "SpotInstanceRequests[%i].LaunchSpecification.{Type:InstanceType}"|grep Type' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s  --query "SpotInstanceRequests[%i].LaunchSpecification.Placement.{AZone:AvailabilityZone}" | grep AZone' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	spotPrice=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s  --query "SpotInstanceRequests[%i].{Price:SpotPrice}" | grep Price' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	
	if spotStatus == 'active':
		instanceID=subprocess.Popen('aws ec2 describe-spot-instance-requests --region %s --query "SpotInstanceRequests[%i].{InstanceID:InstanceId}"|grep InstanceID' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]	
		status=subprocess.Popen('aws ec2 describe-instances --instance-id %s --region %s  --query "Reservations[0].Instances[*].State" | grep Name' %(instanceID,region),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1] 
		if status == 'running':
			PublicIP=subprocess.Popen('aws ec2 describe-instances --region %s  --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(region,instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]	
		status='%s\t'%(status)
			
        print '%s\t\t%s\t%s\t%s\t\t%s\t%s\t%s\t$%1.3f' %(instanceType,availZone,spotID,spotStatus,instanceID,status,PublicIP,float(spotPrice))

        counter=counter+1

#Get number of instances to loop over
numVols=subprocess.Popen('aws ec2 describe-volumes --region %s  --query "Volumes[*].{VolumeID:VolumeId}" | grep VolumeID | wc -l' %(region) ,shell=True, stdout=subprocess.PIPE).stdout.read().strip()

counter=0

print '\n----------------------------------------------------------------------------------------'
print 'Volume ID\tAvail. Zone\tSize\tUser\t\tStatus\t\tInstance'
print '----------------------------------------------------------------------------------------'

if float(numVols) == 0:
	print 'No volumes found\n'

while counter < float(numVols): 

	volumeID=subprocess.Popen('aws ec2 describe-volumes --region %s --query "Volumes[%i].{VolumeID:VolumeId}" | grep VolumeID' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	status=subprocess.Popen('aws ec2 describe-volumes  --region %s  --query "Volumes[%i].{State:State}" | grep State' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-volumes  --region %s --query "Volumes[%i].{AvailZone:AvailabilityZone}" | grep AvailZone' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	size=subprocess.Popen('aws ec2 describe-volumes  --region %s  --query "Volumes[%i].{Size:Size}" | grep Size' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1]

	if status == 'in-use':
		instance=subprocess.Popen('aws ec2 describe-volumes  --region %s  --query "Volumes[%i].Attachments[*].{InstanceID:InstanceId}" | grep InstanceID' %(region,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

		print '%s\t%s\t%sGB\t%s\t\t%s' %(volumeID,availZone,size,status,instance)
	if status != 'in-use':
	
		print '%s\t%s\t%sGB\t%s\t---' %(volumeID,availZone,size,status)

	counter=counter+1

print '\n'
