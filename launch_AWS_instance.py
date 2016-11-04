#!/usr/bin/env python
import os
import sys
import subprocess
import linecache
import time
from optparse import OptionParser
import optparse

#=========================
def setupParserOptions():
    parser = optparse.OptionParser()
    parser.set_usage("awslaunch --instance=<instanceType>")
    parser.add_option("--instance",dest="instance",type="string",metavar="STRING",
            help="Specify instance type to launch")
    parser.add_option("--availZone",dest="zone",type="string",metavar="STRING",
            help="Specify availability zone")
    parser.add_option("--spotPrice",dest="spot",type="float",metavar="FLOAT",default=-1,
            help="Optional: Specify spot price (if spot instance requested)")
    parser.add_option("--instanceList", action="store_true",dest="listInstance",default=False,
            help="Flag to list available instances")
    parser.add_option("-d", action="store_true",dest="debug",default=False,
            help="debug")
    options,args = parser.parse_args()

    if len(args) > 0:
            parser.error("Unknown commandline options: " +str(args))

    if len(sys.argv) < 2:
            parser.print_help()
            sys.exit()
    params={}
    for i in parser.option_list:
            if isinstance(i.dest,str):
                    params[i.dest] = getattr(options,i.dest)
    return params

#====================
def checkConflicts(params,availInstances):

    if not params['zone']: 
	print 'Error: No availability zone specified. Exiting'
	sys.exit()

    if params['spot'] <= 0:
	if params['spot'] != -1:
		print 'Error: Spot price requested is less than or equal to 0. Try again. Exiting\n'
		sys.exit()	

    #Check that keypair exists
    keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if len(keyPath) == 0:
    	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
    	sys.exit()
    if not os.path.exists(keyPath):
        print 'Error: Key pair file %s does not exist. Exiting' %(keyPath)
        sys.exit()
    if keyPath.split('/')[-1].split('.')[-1] != 'pem':
    	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
    	sys.exit()

    #Check that enviornmental variables are set
    AWS_ACCESS_KEY_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_SECRET_ACCESS_KEY=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_ACCOUNT_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

    if len(AWS_ACCESS_KEY_ID) == 0:
    	print '\nError: AWS_ACCESS_KEY_ID not specified as environment variable. Exiting\n'
    	sys.exit()
    if len(AWS_SECRET_ACCESS_KEY) == 0:
    	print '\nError: AWS_SECRET_ACCESS_KEY not specified as environment variable. Exiting\n'
    	sys.exit()
    if len(AWS_ACCOUNT_ID) == 0:
    	print '\nError: AWS_ACCOUNT_ID not specified as environment variable. Exiting\n'
    	sys.exit()
    if len(AWS_DEFAULT_REGION) == 0:
    	print '\nError: AWS_DEFAULT_REGION not specified as environment variable. Exiting\n'
    	sys.exit()
    if AWS_DEFAULT_REGION == 'us-east-1':
	if params['instance'].split('.')[0] == 'p2':
        	AMI='ami-69eba27e'
    	if params['instance'].split('.')[0] != 'p2':
        	AMI='ami-ec3a3b84'
    if AWS_DEFAULT_REGION == 'us-west-2':
        if params['instance'].split('.')[0] == 'p2':
		AMI='ami-9caa71fc'
	if params['instance'].split('.')[0] != 'p2':
		AMI='ami-bc08c3dc'

    #Check that instance is in approved list
    if not params['instance'] in availInstances:
        print 'Error: Instance %s is not in instance list' %(params['instance'])
        print availInstances
        sys.exit()

    return keyPath.split('/')[-1].split('.')[0],keyPath,AMI

#==========================
def launchInstance(params,keyName,keyPath,AMI):

    print '\nLaunching AWS instance %s for user %s\n' %(params['instance'],keyName)

    securityGroupName='sg_%i' %(int(time.time()))
    securityGroupDescript='Automated security group'
    IPaddress=subprocess.Popen('curl -s ipecho.net/plain',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if len(IPaddress) == 0:
        print 'Error: Could not get IP address of your computer. Exiting.'
        sys.exit()

    if params['debug'] is True:
        print 'Current IP address=%s/32' %(IPaddress)

    if params['debug'] is True:
    	print '\nConfiguring security group %s to use IP address %s/32 ...' %(securityGroupName,IPaddress)

    print '\nConfiguring security settings ...\n'

    #Get VPC ID for 'default' VPC:
    #Strategy: List all VPCs, then loop through to get any default VPC
    #Get number of VPCs available to user
    numVPCs=float(subprocess.Popen('aws ec2 describe-vpcs --query "Vpcs[*].{VPC:VpcId}" | grep VPC | wc -l', shell=True, stdout=subprocess.PIPE).stdout.read().strip())

    if params['debug'] is True:
    	print 'Number of VPCs=%0.f\n' %(numVPCs)
    if numVPCs == 0:
    	print 'Error: No VPCs found. Exiting'
    	sys.exit()

    ##Loop over all VPCs
    vpcCounter=0
    while vpcCounter < numVPCs:
    	if int(subprocess.Popen('aws ec2 describe-vpcs --query "Vpcs[%0.f].{Check:IsDefault}" | grep true | wc -l' %(vpcCounter), shell=True, stdout=subprocess.PIPE).stdout.read().strip()) == 1:
    		VPC=subprocess.Popen('aws ec2 describe-vpcs --query Vpcs[%0.f].{vpc:VpcId} | grep vpc-'%(vpcCounter), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
    		if params['debug'] is True:
    			print 'Default VPC=%s\n' %(VPC)
    	vpcCounter=vpcCounter+1

    if params['debug'] is True:
    	print '\nAdding security group into VPC %s ...\n' %(VPC)

    ##Create security group for given IP address
    ##Check if there are more than 500 security groups. If so, throw error

    numSecurityGroups=subprocess.Popen('aws ec2 describe-security-groups --query "SecurityGroups[*].{Groups:GroupName}" | grep Groups| wc -l', shell=True, stdout=subprocess.PIPE).stdout.read().strip()

    if params['debug'] is True:
    	print 'Number of Security Groups=%s\n' %(numSecurityGroups)

    if int(numSecurityGroups) >= 499:
    	print 'Error: Too many security groups. Exiting\n'
    	sys.exit()

    securityGroupId=subprocess.Popen('aws ec2 create-security-group --group-name %s --vpc-id %s --description "%s" | grep GroupId' %(securityGroupName,VPC,securityGroupDescript), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

    if params['debug'] is True:
    	print 'Security Group Name=%s' %(securityGroupName)
    	print 'Security Group ID=%s' %(securityGroupId)

    cmd='aws ec2 authorize-security-group-ingress --group-id %s --protocol tcp --port 22 --cidr %s/32' %(securityGroupId,IPaddress)
    if params['debug'] is True:
    	print cmd
    subprocess.Popen(cmd,shell=True).wait()

    if params['spot'] == -1:
	    print '\nBooting up instance ...\n'
	    InstanceID=subprocess.Popen('aws ec2 run-instances --placement AvailabilityZone=%s --image-id %s --key-name %s --instance-type %s --count 1 --security-groups %s --query "Instances[0].{instanceID:InstanceId}"|grep instanceID' %(params['zone'],AMI,keyName,params['instance'],securityGroupName), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
   
   	    Status='init'
    	    while Status != 'running':
	    	Status=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{State:State}" | grep Name' %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

        	if params['debug'] is True:
                	print Status
        	if Status != 'running':
                	time.sleep(10)

    	    if params['debug'] is True:
        	print 'Now waiting for SysStatus and InsStatus..'

    	    SysStatus='init'
   	    InsStatus='init'

    	    print '\nWaiting for instance to pass system checks ...\n'

	    while SysStatus != 'ok' and InsStatus != 'ok':
	    	SysStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		InsStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		time.sleep(4)
 	    #Get public IP address
       	    PublicIP=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	   #Tag instance using keyname (which should be username, region)
            if params['debug'] is True:
        	print '\nTagging instance %s with your key pair name %s\n' %(InstanceID,keyName)
    	    cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value=%s' %(InstanceID,keyName)
    	    subprocess.Popen(cmd,shell=True).wait()

    	    #Once ready, print command to terminal for user to log in:
    	    print '\nInstance is ready! To log in:\n'
    	    print 'ssh -X -i %s ubuntu@%s' %(keyPath,PublicIP)

    if params['spot'] >0: 
	    if os.path.exists('inputjson.json'):
		os.remove('inputjson.json')
 	    #Write json
	    json='{\n'
  	    json+='\t"ImageId": "%s",\n' %(AMI)
	    json+='\t"KeyName": "%s",\n' %(keyName)
  	    json+='\t"SecurityGroupIds": [ "%s" ],\n' %(securityGroupId)
	    json+='\t"InstanceType": "%s",\n'%(params['instance'])
	    json+='\t"Placement": {\n'
	    json+='\t\t"AvailabilityZone": "%s"\n' %(params['zone'])
	    json+='\t}\n'
	    json+='}\n'
	    jsonF = open('inputjson.json','w')
 	    jsonF.write(json)
	    jsonF.close()

	    SpotInstanceID=subprocess.Popen('aws ec2 request-spot-instances --type "one-time" --spot-price "%f" --instance-count 1 --launch-specification file://inputjson.json | grep SpotInstanceRequestId' %(params['spot']), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	    cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value=%s' %(SpotInstanceID,keyName)
            subprocess.Popen(cmd,shell=True).wait() 

	    print 'Spot instance request submitted.\n'

#==============================
if __name__ == "__main__":

    availInstances=['t2.micro','t2.nano','t2.small','t2.medium','t2.large','m4.large','m4.xlarge','m4.2xlarge','m4.4xlarge','m4.10xlarge','m4.16xlarge','m3.medium','m3.large','m3.xlarge','m3.2xlarge','c4.large','c4.xlarge','c4.2xlarge','c4.4xlarge','c4.8xlarge','c3.large','c3.xlarge','c3.2xlarge','c3.4xlarge','c3.xlarge','r3.large','r3.xlarge','r3.2xlarge','r3.4xlarge','r3.8xlarge','p2.xlarge','p2.8xlarge','g2.2xlarge','g2.8xlarge']

    params=setupParserOptions()
    if params['listInstance'] is True:
        print 'Available instances:'
        print availInstances
        sys.exit()

    #Need to check if they ask for p2 that they are in Oregon, Virginia, or Ireland

    #Need to create directory for AMIs across regions. Right now, just US-East-1 
    keyName,keyPath,AMI=checkConflicts(params,availInstances)
    launchInstance(params,keyName,keyPath,AMI)
