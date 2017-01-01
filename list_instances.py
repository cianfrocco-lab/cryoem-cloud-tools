#!/usr/bin/env python

import subprocess
import os
import sys 
import linecache
clusterlist=False
if sys.argv[-1] == '-c':
	clusterlist=True

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]
AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
print '\nAWS EC2 information for user %s in region %s' %(tag,AWS_DEFAULT_REGION)

#Get number of instances to loop over
numInstances=subprocess.Popen('aws ec2 describe-instances --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Reservations[*].Instances[*].{InstanceID:InstanceId}" | grep InstanceID | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\n----------------------------------------------------------------------------------------------------'
print 'InstanceType\tAvail. Zone\tInstanceID\t\tStatus\t\tUser\t\tLogin info'
print '----------------------------------------------------------------------------------------------------'

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
	if status == 'running':
		status='running\t'	
	print '%s\t%s\t%s\t%s\t%s\t%s' %(instanceType,availZone,instanceID,status,tag,PublicIP)

	counter=counter+1

#Info needed: instance ID, AMI, region, zone, tag
numSpotInstances=subprocess.Popen('aws ec2 describe-spot-instance-requests --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "SpotInstanceRequests[*].{State:State}"|grep State | wc -l' %(tag),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
counter=0

print '\n-----------------------------------------------------------------------------------------------------------------------------------------------'
print 'SpotInstanceType\tAvail. Zone\tSpotInstanceID\tSpotStatus\tInstanceID\t\tStatus\t\tPrice\tUser\t\tLogin info'
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

print '\n----------------------------------------------------------------------------------------------------------'
print 'Volume ID\t\tDescription\t\tAvail. Zone\tSize\tUser\t\tStatus\t\tInstance'
print '----------------------------------------------------------------------------------------------------------'

if float(numVols) == 0:
	print 'No volumes found\n'

while counter < float(numVols): 
	nameVol='N/A\t'
	volumeID=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{VolumeID:VolumeId}" | grep VolumeID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	status=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{State:State}" | grep State' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	availZone=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{AvailZone:AvailabilityZone}" | grep AvailZone' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	size=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].{Size:Size}" | grep Size' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1]
	description=subprocess.Popen('aws ec2 describe-volumes  --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].Tags[*].{Key:Key}" | grep Key' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()
	count2=1
	while count2 <= len(description):
		if description[count2-1] == '"Name"':
			value=subprocess.Popen('aws ec2 describe-volumes  --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].Tags[*].{Value:Value}" | grep Value' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
			nameVol=value.split('"')[count2*2-1]
			if len(nameVol) <8: 
				nameVol=nameVol+'\t'	
		count2=count2+1
	if status == 'in-use':
		instance=subprocess.Popen('aws ec2 describe-volumes --filter Name=tag-key,Values=Owner,Name=tag-value,Values=%s --query "Volumes[%i].Attachments[*].{InstanceID:InstanceId}" | grep InstanceID' %(tag,counter),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

		print '%s\t%s\t%s\t%sGB\t%s\t%s\t\t%s' %(volumeID,nameVol,availZone,size,tag,status,instance)
	if status != 'in-use':
	
		print '%s\t%s\t%s\t%sGB\t%s\t%s\t--' %(volumeID,nameVol,availZone,size,tag,status)

	counter=counter+1

if clusterlist is False:
	print '\n'
	sys.exit()

starcluster=subprocess.Popen('which starcluster',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
if len(starcluster) == 0:
	sys.exit()
print '\n----------------------------------------------------------------------------------------'
print 'STARcluster software: Cluster management on AWS '
print '----------------------------------------------------------------------------------------'

if not os.path.exists('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())):
        os.makedirs('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()))

if not os.path.exists('%s/.starcluster/config' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())):
        AWS_ACCESS_KEY_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_SECRET_ACCESS_KEY=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_ACCOUNT_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        cmd='####################################\n'        
	cmd+='## StarCluster Configuration File ##\n'
        cmd+='####################################\n'        
	cmd+='[aws info]\n'
        cmd+='AWS_USER_ID=%s\n' %(AWS_ACCOUNT_ID)
        cmd+='AWS_ACCESS_KEY_ID =%s\n' %(AWS_ACCESS_KEY_ID)
        cmd+='AWS_SECRET_ACCESS_KEY = %s\n' %(AWS_SECRET_ACCESS_KEY)        
	cmd+='AWS_REGION_NAME = %s\n' %(AWS_DEFAULT_REGION)
        #cmd+='AVAILABILITY_ZONE = %s\n' %(params['zone'])
        cmd+='AWS_REGION_HOST = ec2.%s.amazonaws.com\n' %(AWS_DEFAULT_REGION)
        cmd+='[global]\n'
        cmd+='DEFAULT_TEMPLATE=cluster\n'
        cmd+='[key %s]\n' %(keyPath.split('/')[-1].split('.')[0])
        cmd+='KEY_LOCATION=%s\n' %(keyPath)

	o1=open('%s/.starcluster/config' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()),'w')
        o1.write(cmd)
        o1.close()
if os.path.exists('tmpstar3344.txt'):
	os.remove('tmpstar3344.txt')

cmd='starcluster listclusters > tmpstar3344.txt'
subprocess.Popen(cmd,shell=True).wait()

print '********************************************************************************************'
print 'Cluster name\t\t\t#Nodes\tUptime\t\tAvail. Zone\tEBS Volume\tLogin info'
print '********************************************************************************************'

totlines=len(open('tmpstar3344.txt','r').readlines())
if totlines < 5: 
	print 'No active clusters found\n'	
	sys.exit()

counter=1
while counter <= totlines:
	line=linecache.getline('tmpstar3344.txt',counter)
	if line[0] == '-': 
		if linecache.getline('tmpstar3344.txt',counter+2)[0] == '-': 
			clustername=linecache.getline('tmpstar3344.txt',counter+1).split('@sc-')[-1][:-2]
			uptime=linecache.getline('tmpstar3344.txt',counter+4).split()[-1]
			zone=linecache.getline('tmpstar3344.txt',counter+7).split()[-1]			
			ebsvol=linecache.getline('tmpstar3344.txt',counter+9).split()[-1]  
			if len(ebsvol) < 5:
				ebsvol=ebsvol+'\t'
			if len(ebsvol) > 5: 
				ebsvol=linecache.getline('tmpstar3344.txt',counter+10).split()[0]
			#Loop to get number of nodes
			newcounter=0	
			maximum=20
			while newcounter <= maximum: 
				newline=linecache.getline('tmpstar3344.txt',counter+9+newcounter)
				if newline.split()[0] == 'Total': 
					num=newline.split()[-1]
					newcounter=50
				newcounter=newcounter+1
			login='starcluster sshmaster %s -X -u ubuntu' %(clustername)	
			print '%s\t%s\t%s\t%s\t%s\t%s' %(clustername,num,uptime,zone,ebsvol,login)
	counter=counter+1

print '\n'

#os.remove('tmpstar3344.txt')
