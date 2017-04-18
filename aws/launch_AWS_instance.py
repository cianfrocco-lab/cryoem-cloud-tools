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
    parser.add_option("--volume",dest="volume",type="string",metavar="STRING",default='None',
            help="Optional: Specifiy volume ID to be mounted onto instance (Must be same avail. zone)")
    parser.add_option("--relion2",action="store_true",dest="relion2",default=False,
            help="Optional: Flag to use relion2 environment on non-GPU machines (By default, relion2 software is only loaded onto GPU (p2) instances)") 
    parser.add_option("--AMI",dest="AMI",type="string",metavar="STRING",default='None',
            help="Optional: Specifiy AMI to use when booting instance (Must be in same region, overrides any other AMI)")
    parser.add_option("--noEBS",action="store_true",dest="force",default=False,
            help="Optional: Force boot up without attached EBS volume")
    parser.add_option("--alwaysOn",action="store_true",dest="cloudskip",default=False,
	    help="Optional: Force instance to remain on always (when this option is not specified, instance will be terminated after 30 minutes of idle time)")
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

    allowedzones=['us-east-1c','us-east-1b','us-east-1d','us-east-1e','us-east-1a','us-west-2a','us-west-2b','us-west-2c','us-west-1a', 'us-west-1b','us-west-1c','eu-west-1a','eu-west-1b','eu-west-1c','ap-southeast-1a','ap-southeast-1b','ap-northeast-1a','ap-northeast-1b','ap-northeast-1c','ap-southeast-2a','ap-southeast-2b','sa-east-1a','sa-east-1b','us-east-2a','us-east-2b','us-east-2c','ca-central-1a','ca-central-1b','eu-west-2a','eu-west-2b','eu-central-1a','eu-central-1b','ap-northeast-2a','ap-northeast-2c','ap-south-1a','ap-south-1b']

    gpuzones=['us-east-1c','us-east-1b','us-east-1d','us-east-1e','us-east-1a','us-west-2a','us-west-2b','us-west-2c','eu-west-1a','eu-west-1b','eu-west-1c']

    if params['zone'] not in allowedzones: 
	print 'Error: Input zone %s is not in allowed zones:' %(params['zone'])
	print allowedzones
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
    if params['instance'].split('.')[0] == 'p2':
	if params['zone'] not in gpuzones: 
		print 'Error: Specified availability zone %s does not have GPU instances (p2). Please use one of the availability zones (regions) below:' %(params['zone'])
		print gpuzones
		sys.exit()

    if AWS_DEFAULT_REGION == 'us-east-1':
	if params['instance'].split('.')[0] == 'p2':
        	AMI='ami-69eba27e'
    	if params['instance'].split('.')[0] != 'p2':
        	AMI='ami-ec3a3b84'
	if params['relion2'] is True:
		AMI='ami-69eba27e'
    if AWS_DEFAULT_REGION == 'us-west-2':
        if params['instance'].split('.')[0] == 'p2':
		AMI='ami-26139046'
	if params['instance'].split('.')[0] != 'p2':
		AMI='ami-bc08c3dc'
	if params['relion2'] is True:
		AMI='ami-26139046'
    if params['AMI'] != 'None': 
        AMI=params['AMI']

    #Check that instance is in approved list
    if not params['instance'] in availInstances:
        print 'Error: Instance %s is not in instance list' %(params['instance'])
        print availInstances
        sys.exit()

    return keyPath.split('/')[-1].split('.')[0],keyPath,AMI,AWS_ACCOUNT_ID

#==========================
def launchInstance(params,keyName,keyPath,AMI,AWS_ACCOUNT_ID):

    print '\nLaunching AWS instance %s for user %s\n' %(params['instance'],keyName)

    uname=subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    securityGroupName='sg_%i' %(int(time.time()))
    securityGroupDescript='Automated security group'
    #if uname == 'Linux': 
    IPaddress=subprocess.Popen('curl ipecho.net/plain; echo',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    #if uname == 'Darwin': 
	#IPaddress=subprocess.Popen('curl ipecho.net/plain ; echo',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if len(IPaddress) == 0:
        print 'Error: Could not get IP address of your computer. Exiting.'
        sys.exit()
    if params['debug'] is True:
        print 'Current IP address=%s/32' %(IPaddress)

    #Check if IP address already has security group
    numSecurityGroups=float(subprocess.Popen('aws ec2 describe-security-groups --query "SecurityGroups[*].{SG:GroupName}" | grep SG | wc -l', shell=True, stdout=subprocess.PIPE).stdout.read().strip())
    SGexist=False
    SGGroupName=''
    SGcounter=0 
    while SGcounter < numSecurityGroups: 
	cmd='aws ec2 describe-security-groups --query "SecurityGroups[%i].IpPermissions[*]" | grep Cidr > cidrtmp.log' %(SGcounter)
	if params['debug'] is True:
		print cmd
	subprocess.Popen(cmd,shell=True).wait()
    	r1=open('cidrtmp.log','r')
    	for l1 in r1:	
		sgIP=l1.split(':')[-1].split('"')[1]	
        	if params['debug'] is True: 
			print sgIP
		if sgIP == IPaddress+'/32': 
			if params['debug'] is True: 
				print 'matched'
			SGout=subprocess.Popen('aws ec2 describe-security-groups --query "SecurityGroups[%i].IpPermissions[*]"' %(SGcounter), shell=True, stdout=subprocess.PIPE).stdout.read().strip()
			if SGout != 'null': 
				SGGroupName=subprocess.Popen('aws ec2 describe-security-groups --query "SecurityGroups[%i]" | grep GroupName' %(SGcounter), shell=True, stdout=subprocess.PIPE).stdout.read().strip()
				if len(SGGroupName) > 0: 
					securityGroupName=SGGroupName.split(':')[-1].split('"')[1]	
					SGexist=True
    	r1.close()
    	os.remove('cidrtmp.log')
    	SGcounter=SGcounter+1

    if params['debug'] is True:
	print securityGroupName
    	print SGexist
    if SGexist is False:
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
	    InstanceID=subprocess.Popen('aws ec2 run-instances --placement AvailabilityZone=%s --image-id %s --key-name %s --instance-type %s --count 1 --security-group-ids %s --query "Instances[0].{instanceID:InstanceId}" | grep instanceID' %(params['zone'],AMI,keyName,params['instance'],securityGroupName), shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	    if len(InstanceID) == 0:
		awsclidir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		numRunning=subprocess.Popen('%s/list_all.py %s -i | grep %s  | grep running | wc -l' %(awsclidir,params['zone'][:-1],params['instance']), shell=True, stdout=subprocess.PIPE).stdout.read().strip() 
	   	if len(numRunning) == 0: 
			numRunning=str(0)
		print '\nError: Could not boot up requested instance. It is likely that you exceeded your limit for your AWS account.'
		print '\nCurrently, there are %s instances of %s running in region %s' %(numRunning,params['instance'],params['zone'][:-1])
		print '\nTo increase your limit, please see http://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html.\n'
		sys.exit()
	    InstanceID=InstanceID.split()[-1].split('"')[1]
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

	    pwd=os.getcwd()
	    cmd='aws ec2 create-tags --resources %s --tags Key=Directory,Value=%s' %(InstanceID,pwd)
	    subprocess.Popen(cmd,shell=True).wait()

	    if params['cloudskip'] is False: 
		if params['debug'] is True:
                	print '\nAttaching cloud watch to instance...\n'
		cmd='aws cloudwatch put-metric-alarm --alarm-name %s --alarm-description "Alarm when 0 per usage" --metric-name CPUUtilization --namespace AWS/EC2 --statistic Average --period 60 --threshold 10 --comparison-operator LessThanOrEqualToThreshold --dimensions "Name=InstanceId,Value=%s" --evaluation-periods 60 --alarm-actions arn:aws:swf:%s:%s:action/actions/AWS_EC2.InstanceId.Terminate/1.0 --actions-enabled' %(InstanceID,InstanceID,params['zone'][:-1],AWS_ACCOUNT_ID)
	    	if params['debug'] is True:
			print cmd
	    	subprocess.Popen(cmd,shell=True).wait()

    	    #Once ready, print command to terminal for user to log in:
    	    print '\nInstance is ready! To log in:\n'
    	    print 'ssh -X -i %s ubuntu@%s' %(keyPath,PublicIP)
	    print '\nID: %s\n' %(InstanceID)

	    return InstanceID,PublicIP

    if params['spot'] >0: 
	    if os.path.exists('inputjson.json'):
		os.remove('inputjson.json')
 	    #Write json
	    json='{\n'
  	    json+='\t"ImageId": "%s",\n' %(AMI)
	    json+='\t"KeyName": "%s",\n' %(keyName)
  	    json+='\t"SecurityGroupIds": [ "%s" ],\n' %(securityGroupName)
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

#======================
def AttachMountEBSVol(instanceID,volID,PublicIP,keyPath):

   fabric_test=module_exists('fabric.api')
   if fabric_test is False:
       print 'Error: Could not find fabric installed and it is required. Install from here: http://www.fabfile.org/installing.html'
       sys.exit()
   #Import Fabric modules now: 
   from fabric.operations import run, put
   from fabric.api import env,run,hide,settings
   from fabric.context_managers import shell_env
   from fabric.operations import put

   #List instances given a users tag
   keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

   tag=keyPath.split('/')[-1].split('.')[0]

   print '\n\nAttaching volume %s to instance %s ...\n' %(volID,instanceID)

   SysStatus='init'
   InsStatus='init'

   while SysStatus != 'ok' and InsStatus != 'ok':
        SysStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
        InsStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
        time.sleep(4)

   volID=subprocess.Popen('aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdf > tmp3re3333.log' %(volID,instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()

   time.sleep(3)
   if os.path.exists('tmp3re3333.log'):
	os.remove('tmp3re3333.log')
   time.sleep(10)
   env.host_string='ubuntu@%s' %(PublicIP)
   env.key_filename = '%s' %(keyPath)
   dir_exists=exec_remote_cmd('ls /data')
   if len(dir_exists.split()) >0: 
	if dir_exists.split()[2] == 'access': 
		mk=exec_remote_cmd('sudo mkdir /data/') 
   check_NFS=exec_remote_cmd('sudo file -s /dev/xvdf')
   if 'filesystem' not in check_NFS:
	nfsmount=exec_remote_cmd('sudo mkfs -t ext4 /dev/xvdf')
   mount_out=exec_remote_cmd('sudo mount /dev/xvdf /data')
   chmod=exec_remote_cmd('sudo chmod 777 /data/')
   if 'filesystem' not in check_NFS:
	chmod=exec_remote_cmd('rm /data/lost+found')
   print '\n...volume mounted onto /data/ ...\n' 

#====================
def module_exists(module_name):
        try:
                __import__(module_name)
        except ImportError:
                return False
        else:
                return True

#====================
def exec_remote_cmd(cmd):
    from fabric.operations import run, put
    from fabric.api import hide,settings
    with hide('output','running','warnings'), settings(warn_only=True):
        return run(cmd)

#==============================
def query_yes_no(question, default="no"):
	valid = {"yes": True, "y": True, "ye": True,"no": False, "n": False}
	if default is None:
		prompt = " [y/n] "
	elif default == "yes":
		prompt = " [Y/n] "
	elif default == "no":
		prompt = " [y/N] "
	else:
		raise ValueError("invalid default answer: '%s'" % default)
	while True:
		sys.stdout.write(question + prompt)
		choice = raw_input().lower()
		if default is not None and choice == '':
			return valid[default]
		elif choice in valid:
			return valid[choice]
		else:
			sys.stdout.write("Please respond with 'yes' or 'no' "
					 "(or 'y' or 'n').\n")

#==============================
if __name__ == "__main__":

    availInstances=['t2.micro','t2.nano','t2.small','t2.medium','t2.large','i2.2xlarge','i2.xlarge','m4.large','m4.xlarge','m4.2xlarge','m4.4xlarge','m4.10xlarge','m4.16xlarge','m3.medium','m3.large','m3.xlarge','m3.2xlarge','c4.large','c4.xlarge','c4.2xlarge','c4.4xlarge','c4.8xlarge','c3.large','c3.xlarge','c3.2xlarge','c3.4xlarge','c3.xlarge','r4.16xlarge','r4.4xlarge','r4.8xlarge','r3.large','r3.xlarge','r3.2xlarge','r3.4xlarge','r3.8xlarge','p2.xlarge','p2.8xlarge','p2.16xlarge','g2.2xlarge','g2.8xlarge']

    params=setupParserOptions()
    if params['listInstance'] is True:
        print 'Available instances:'
        print availInstances
	if params['volume'] != 'None':
		print 'Volume cannot be attached with spot instances at this time. (Work in progress)\n'
        sys.exit()
    if params['volume'] == 'None': 
	if params['force'] is False: 
		qans=query_yes_no('\nAre you sure you want to boot up this instance without an EBS volume?')
		if qans is False: 
			sys.exit() 

    #Need to create directory for AMIs across regions. Right now, just US-East-1 
    keyName,keyPath,AMI,AWS_ACCOUNT_ID=checkConflicts(params,availInstances)
    instanceID,PublicIP=launchInstance(params,keyName,keyPath,AMI,AWS_ACCOUNT_ID)
    if params['volume'] != 'None': 
	AttachMountEBSVol(instanceID,params['volume'],PublicIP,keyPath)



