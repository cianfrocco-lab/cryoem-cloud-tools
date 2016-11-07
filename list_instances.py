#!/usr/bin/env python

import subprocess
import os
import sys 

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
numInstances=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[*].Instances[*].{InstanceID:InstanceId}" | grep InstanceID | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\n---------------------------------------------------------------------------------------------'
print 'InstanceType\tAvail. Zone\tInstanceID\tStatus\t\tUser\t\tLogin info'
print '---------------------------------------------------------------------------------------------'

if float(numInstances) == 0:
	print 'No instances found'

while counter < float(numInstances): 
	instanceID=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{InstanceID:InstanceId}" | grep InstanceID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	if len(instanceID) > 0:
		instanceID=instanceID.split()[-1].split('"')[1]
	if len(instanceID) == 0:
		instanceID='---'
	status=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{State:State}" | grep Name' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	instanceType=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*].{Type:InstanceType}" | grep Type' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[%i].Instances[*]" | grep AvailabilityZone' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	PublicIP=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	
	if len(PublicIP) > 0:
		
		if PublicIP[0] == '"':
			PublicIP=PublicIP.split()[-1].split('"')
			if len(PublicIP)>1:
				PublicIP='ssh -X -i %s '%(keyPath)+'ubuntu@%s'%(PublicIP[1])
			if len(PublicIP)==1:
				PublicIP=PublicIP[0]
				if PublicIP == 'null':
					PublicIP='---\t'
	if len(PublicIP) == 0:
		PublicIP='---'
	
	print '%s\t%s\t%s\t%s\t%s\t%s' %(instanceType,availZone,instanceID,status,tag,PublicIP)

	counter=counter+1

#Info needed: instance ID, AMI, region, zone, tag
numSpotInstances=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[*].{State:State}"|grep State | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\n-----------------------------------------------------------------------------------------------------------------------------------------------'
print 'SpotInstanceType\tAvail. Zone\tSpotInstanceID\tSpotStatus\tInstanceID\tStatus\t\tPrice\tUser\t\tLogin info'
print '-----------------------------------------------------------------------------------------------------------------------------------------------'

if float(numSpotInstances) == 0:
        print 'No spot instances found'

while counter < float(numSpotInstances):
	instanceID='---\t'
	status='---\t'
	PublicIP='---\t\t'
	spotID=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].{SpotID:SpotInstanceRequestId}"|grep SpotID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	spotStatus=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].{State:State}"|grep State' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	instanceType=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].LaunchSpecification.{Type:InstanceType}"|grep Type' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].LaunchSpecification.Placement.{AZone:AvailabilityZone}" | grep AZone' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	spotPrice=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].{Price:SpotPrice}" | grep Price' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	
	if spotStatus == 'active':
		instanceID=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[%i].{InstanceID:InstanceId}"|grep InstanceID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]	
		status=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[0].Instances[*].State" | grep Name' %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1] 
		if status == 'running':
			PublicIP='ssh -X -i %s '%(keyPath)+'ubuntu@'+subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]	
		status='%s\t'%(status)
			
        print '%s\t\t%s\t%s\t%s\t\t%s\t%s\t$%1.3f\t%s\t%s' %(instanceType,availZone,spotID,spotStatus,instanceID,status,float(spotPrice),tag,PublicIP)

        counter=counter+1

#Get number of instances to loop over
numVols=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[*].{VolumeID:VolumeId}" | grep VolumeID | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()

counter=0

print '\n----------------------------------------------------------------------------------------'
print 'Volume ID\tAvail. Zone\tSize\tUser\t\tStatus\t\tInstance'
print '----------------------------------------------------------------------------------------'

if float(numVols) == 0:
	print 'No volumes found\n'

while counter < float(numVols): 

	volumeID=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{VolumeID:VolumeId}" | grep VolumeID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	status=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{State:State}" | grep State' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{AvailZone:AvailabilityZone}" | grep AvailZone' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	size=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{Size:Size}" | grep Size' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1]

	if status == 'in-use':
		instance=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].Attachments[*].{InstanceID:InstanceId}" | grep InstanceID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

		print '%s\t%s\t%sGB\t%s\t%s\t\t%s' %(volumeID,availZone,size,tag,status,instance)
	if status != 'in-use':
	
		print '%s\t%s\t%sGB\t%s\t%s\t--' %(volumeID,availZone,size,tag,status)

	counter=counter+1

print '\n'
