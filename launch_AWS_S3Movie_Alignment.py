#!/usr/bin/env python
import os
import sys
import subprocess
import linecache
import time
from optparse import OptionParser
import optparse
import math

#=========================
def setupParserOptions():
    parser = optparse.OptionParser()
    parser.set_usage("awslaunch_movieAlign --instance=<instanceType>")
    parser.add_option("--s3",dest="s3",type="string",metavar="STRING",
            help="S3 bucket containing movies with .mrcs extension")
    parser.add_option("--gain",dest="gain",type="string",metavar="STRING",default='gain_ref.mrc',
            help="Gain reference filename (to be found in S3 bucket with movies) (Default = gain_ref.mrc)")
    parser.add_option("--availZone",dest="zone",type="string",metavar="STRING",
            help="Specify availability zone")
    parser.add_option("--motioncor2", action="store_true",dest="motioncor2",default=False,
            help="Flag for MotionCor2 alignment of movies")
    parser.add_option("--dose",dest="dose",type="float",metavar="FLOAT",
            help="Dose rate for dose weighting (e- per Angstroms^2 / frame)")
    parser.add_option("--kev",dest="kev",type="int",metavar="INTEGER",
            help="Accelerating voltage for dose weighting")
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
def checkConflicts(params,instanceType):

    if not params['zone']: 
	print 'Error: No availability zone specified. Exiting'
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
	if instanceType.split('.')[0] == 'p2':
        	AMI='ami-69eba27e'
    	if instanceType.split('.')[0] != 'p2':
        	AMI='ami-ec3a3b84'
    if AWS_DEFAULT_REGION == 'us-west-2':
        if instanceType.split('.')[0] == 'p2':
		AMI='ami-9caa71fc'
	if instanceType.split('.')[0] != 'p2':
		AMI='ami-bc08c3dc'

    return keyPath.split('/')[-1].split('.')[0],keyPath,AMI,AWS_DEFAULT_REGION

#==========================
def launchInstances(params,keyName,keyPath,AMI,numInstances,movielist,instanceType):

    if numInstances == 1:
    	print '\nLaunching AWS instance %s for user %s\n' %(instanceType,keyName)
    if numInstances > 1:
	print '\nLaunching %i AWS instances %s for user %s\n' %(numInstances,instanceType,keyName)
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

    if numInstances == 1:
	    print '\nBooting up instance ...\n'
    if numInstances > 1:
	    print '\nBooting up instances ...\n'
    currentInstance=1
    instanceIDList=[]
    while currentInstance <= numInstances:
	    InstanceID=subprocess.Popen('aws ec2 run-instances --placement AvailabilityZone=%s --image-id %s --key-name %s --instance-type %s --count 1 --security-groups %s --query "Instances[0].{instanceID:InstanceId}"|grep instanceID' %(params['zone'],AMI,keyName,instanceType,securityGroupName), shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	    instanceIDList.append(InstanceID)
	    currentInstance=currentInstance+1

    if numInstances == 1:
	    print '\nWaiting for instance to pass system checks ...\n'
    if numInstances > 1:
	    print '\nWaiting for instances to pass system checks ...\n'

    SysStatus='init'
    InsStatus='init'

    allOK=0

    for InstanceID in instanceIDList:
    	Status='init'
	while Status != 'running':
		Status=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{State:State}" | grep Name' %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	        if params['debug'] is True:
        	       	print Status
			print InstanceID
                time.sleep(10)

    if params['debug'] is True:
     	print 'Instances running, now waiting for system checks'
    instanceDict={}
    while allOK < 1:
        numRunning=0
	for InstanceID in instanceIDList:
		SysStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
 		InsStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
		 
	        if SysStatus == 'ok' and InsStatus == 'ok':
			numRunning=numRunning+1
			print 'Number of instances booted up: %i out of %i requested' %(numRunning,numInstances)
 		        #Get public IP address
			PublicIP=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{IPaddress:PublicIpAddress}" | grep IPaddress' %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
			#Tag instance using keyname (which should be username, region)
			if params['debug'] is True:
			        print '\nTagging instance %s with your key pair name %s\n' %(InstanceID,keyName)
		        cmd='aws ec2 create-tags --resources %s --tags Key=Owner,Value=%s' %(InstanceID,keyName)
		        subprocess.Popen(cmd,shell=True).wait()
			instanceDict[InstanceID]=PublicIP
	if numRunning == numInstances:
		allOK=1
	time.sleep(10)

    return instanceDict
    
#==============================
if __name__ == "__main__":

    params=setupParserOptions()
    if params['listInstance'] is True:
        print 'Available instances:'
        print availInstances
        sys.exit()
    
    if params['motioncor2'] is False:
	print 'Error: No movie alignment software selected. Exiting\n'
	sys.exit()

    if params['motioncor2'] is True:
	instanceType='t2.micro'
        nProcsPerInstance=1
 
    #Need to create directory for AMIs across regions. Right now, just US-East-1 
    keyName,keyPath,AMI,region=checkConflicts(params,instanceType)

    ###################################    
    #Get number of movies in S3 bucket, then calculate number of instances needed to process in under an hour
    ###################################
    #>>> if calc num exceeds limit, use limit. 
    if os.path.exists('~/s3listtmp55555.txt'): 
	os.remove('~/s3listtmp55555.txt')
    	#Get home path
    homepath=subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if params['debug'] is True:
	print 'aws s3 ls %s > %s/s3listtmp55555.txt' %(params['s3'],homepath)
    subprocess.Popen('aws s3 ls %s > %s/s3listtmp55555.txt' %(params['s3'],homepath),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    movielist=[]
    for line in open('%s/s3listtmp55555.txt' %(homepath),'r'):
	if line.split()[-1].split('.')[-1] == 'mrcs':
		movielist.append(line.split()[-1])
    os.remove('%s/s3listtmp55555.txt' %(homepath))
    num=len(movielist)
    if num == 0: 
	print 'Could not find any movies with the .mrcs extension in S3 bucket %s. Exiting' %(params['s3'])
	sys.exit()
    if num > nProcsPerInstance: 
	numInstances=math.ceil(num/nProcsPerInstance)
    if num <=nProcsPerInstance:
	numInstances=1
    if params['debug'] is True:
	print 'Found %i movies, booting up %i instances' %(num,numInstances)
    
    ####################################
    #Boot up instances##################
    ####################################
    #>>>>> Return with instance list containing dict. of IP addresses and instance IDs. Keys are instance IDs, entries are public IPs
    instanceDict=launchInstances(params,keyName,keyPath,AMI,numInstances,movielist,instanceType)

    if params['debug'] is True:
	print 'Dictionary of instanceIDs and IP addresses'
    	print instanceDict

    



