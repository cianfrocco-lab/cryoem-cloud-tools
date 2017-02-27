#!/usr/bin/env python
import os
import sys
import subprocess
import linecache
import time
from optparse import OptionParser
import optparse
import time

#=========================
def setupParserOptions():
    parser = optparse.OptionParser()
    parser.set_usage("awslaunch_cluster --instance=<instanceType>")
    parser.add_option("--instance",dest="instance",type="string",metavar="STRING",
            help="Specify instance type to launch into cluster")
    parser.add_option("--num",dest="num",type="int",metavar="INTEGER",
            help="Number of instances in cluster")
    parser.add_option("--availZone",dest="zone",type="string",metavar="STRING",
            help="Specify availability zone")
    parser.add_option("--volume",dest="ebsvol",type="string",metavar="STRING",default='none',
            help="Optional: Volume ID for volume that will be mounted onto cluster")
    parser.add_option("--spotPrice",dest="spot",type="float",metavar="FLOAT",default=-1,
            help="Optional: Specify spot price (if spot instance requested)")
    parser.add_option("--relion2", action="store_true",dest="relion2",default=False,
            help="Flag to load environment with Relion2 installed")
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
    starcluster=subprocess.Popen('which starcluster',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if len(starcluster) == 0: 
	print '\nError: Cluster creating software (starcluster) is not installed. Install first and then try again.\n'
	sys.exit()
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
    if AWS_DEFAULT_REGION == 'us-west-2':
    	AMI='ami-33291d03'
    	if params['relion2'] is True:
		AMI='ami-dc79dabc'
	
    homedir=subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    starexecpath='%s/.starcluster/config' %(homedir)
    #Check that instance is in approved list
    if not params['instance'] in availInstances:
        print 'Error: Instance %s is not in instance list for creating clusters on AWS' %(params['instance'])
        print availInstances
        sys.exit()

    return keyPath.split('/')[-1].split('.')[0],keyPath,AMI,starexecpath

#==============================
def configStarcluster(params,keyName,keyPath,AMI,starpath):

	if not os.path.exists('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip())):
		os.makedirs('%s/.starcluster' %(subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()))

	if os.path.exists(starpath):
                os.remove(starpath)

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
        cmd+='AVAILABILITY_ZONE = %s\n' %(params['zone'])                                
        cmd+='AWS_REGION_HOST = ec2.%s.amazonaws.com\n' %(AWS_DEFAULT_REGION)
        cmd+='[global]\n'
        cmd+='DEFAULT_TEMPLATE=cluster\n'
        cmd+='[key %s]\n' %(keyName)
        cmd+='KEY_LOCATION=%s\n' %(keyPath)
        cmd+='[cluster cluster]\n'
        cmd+='KEYNAME = %s\n'%(keyName)
        cmd+='CLUSTER_USER = ubuntu\n'
        cmd+='CLUSTER_SHELL = bash\n'
        cmd+='NODE_IMAGE_ID = %s\n' %(AMI)
	if params['spot'] == -1:
		cmd+='FORCE_SPOT_MASTER=False\n'
	if params['spot'] > 0:
		cmd+='FORCE_SPOT_MASTER=True\n'
        cmd+='CLUSTER_SIZE = %i\n' %(params['num'])
        cmd+='NODE_INSTANCE_TYPE = %s\n' %(params['instance'])
	if params['ebsvol'] != 'none':
        	cmd+='VOLUMES = data\n' %()
        	cmd+='[volume data]\n' %()
        	cmd+='VOLUME_ID = %s\n' %(params['ebsvol'])
        	cmd+='MOUNT_PATH = /data\n' %()
   
	o1=open(starpath,'w')
	o1.write(cmd)
	o1.close() 

#==============================
if __name__ == "__main__":

    availInstances=['t2.micro','t2.nano','t2.small','t2.medium','t2.large','m4.large','m4.xlarge','m4.2xlarge','m4.4xlarge','m4.10xlarge','m4.16xlarge','m3.medium','m3.large','m3.xlarge','m3.2xlarge','c4.large','c4.xlarge','c4.2xlarge','c4.4xlarge','c4.8xlarge','c3.large','c3.xlarge','c3.2xlarge','c3.8xlarge','c3.4xlarge','c3.xlarge','r3.large','r3.xlarge','r3.2xlarge','r3.4xlarge','r3.8xlarge']

    params=setupParserOptions()
    if params['listInstance'] is True:
        print 'Available instances:'
        print availInstances
        sys.exit()

    #Need to check if they ask for p2 that they are in Oregon, Virginia, or Ireland

    #Need to create directory for AMIs across regions. Right now, just US-East-1 
    keyName,keyPath,AMI,starpath=checkConflicts(params,availInstances)
    configStarcluster(params,keyName,keyPath,AMI,starpath)
    
    #FIGURE OUT CLUSTER NAMING SCHEME
    clustername='cluster-%s-%0.f' %(params['instance'],time.time())
    if params['spot'] == -1:
    	cmd='starcluster start %s' %(clustername)
	subprocess.Popen(cmd,shell=True).wait()

    if params['spot'] > 0:
        cmd='starcluster start %s --bid=%f' %(clustername,params['spot'])
        subprocess.Popen(cmd,shell=True).wait()



