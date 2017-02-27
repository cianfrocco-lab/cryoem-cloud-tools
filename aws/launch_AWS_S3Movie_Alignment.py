#!/usr/bin/env python
import os
import sys
import subprocess
import linecache
import time
from optparse import OptionParser
import optparse
import math
import random
import string
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
def exec_remote_cmd(cmd):
    with hide('output','running','warnings'), settings(warn_only=True):
        return run(cmd)

#====================
def module_exists(module_name):
	try:
        	__import__(module_name)
        except ImportError:
                return False
        else:
                return True

#====================
def writeDivideScript(homepath):

	cmd='#!/usr/bin/env python\n'
	cmd+='import linecache\n'
	cmd+='import sys\n'
	cmd+='import math\n'
	cmd+='movielist=sys.argv[1]\n'
	cmd+='numProcs=float(sys.argv[2])'
        cmd+='numMovies=len(open(movielist,"r").readlines())\n'
	cmd+='moviesPerProcs=math.ceil(numMovies/float(numProcs))\n'
	cmd+='counter=1\n'
	cmd+='proc=1\n'
	cmd+='while proc <=numProcs:\n'
	cmd+='\to1=open("%s_proc%i.txt" %(movielist[:-4],proc),"w")\n'
	cmd+='\tcounter=1\n'
	cmd+='\twhile counter <= moviesPerProcs:\n'
	cmd+='\t\to1.write(linecache.getline(movielist,int(((proc-1)*moviesPerProcs)+counter)))\n'
	cmd+='\t\tif ((proc-1)*moviesPerProcs)+counter <=numMovies:\n'
	cmd+='\t\t\tprint ((proc-1)*moviesPerProcs)+counter\n'
	cmd+='\t\tcounter=counter+1\n'
	cmd+='\tproc=proc+1\n'

        if os.path.exists('%s/splitscript.py' %(homepath)):
                os.remove('%s/splitscript.py' %(homepath))

        o1=open('%s/splitscript.py' %(homepath),'w')
        o1.write(cmd)
        o1.close()

        return '%s/splitscript.py' %(homepath)

#====================
def writeDownloadScript(homepath):

        cmd='#!/usr/bin/env python\n'
        cmd+='import subprocess\n'
        cmd+='import linecache\n'
        cmd+='import sys\n'
        cmd+='KEYID=sys.argv[1]\n'
        cmd+='SECRET=sys.argv[2]\n'
        cmd+='ID=sys.argv[3]\n'
        cmd+='REGION=sys.argv[4]\n'
        cmd+='totMovies=sys.argv[5]\n'
        cmd+='instanceList=sys.argv[6]\n'
	cmd+='bufferMovie=sys.argv[7]\n'
	cmd+='s3=sys.argv[8]\n'
        cmd+='cmd="export AWS_ACCESS_KEY_ID=%s\n"%(KEYID)\n'
	cmd+='cmd+="export AWS_SECRET_ACCESS_KEY=%s\n" %(SECRET)\n'
	cmd+='cmd+="export AWS_ACCOUNT_ID=%s\n"%(ID)\n'
	cmd+='cmd+="export AWS_DEFAULT_REGION=%s\n"%(REGION)\n'
	cmd+='o1=open("aws_init.sh","w")\n'
	cmd+='o1.write(cmd)\n'
	cmd+='o1.close()\n'
	cmd+='cmd="source aws_init.sh"\n'
	cmd+='subprocess.Popen(cmd,shell=True).wait()\n'
	cmd+='counter=1\n'
	cmd+='if float(bufferMovie) > float(totMovies):\n'
	cmd+='\tbufferMovie=float(totMovies)\n'
        cmd+='while counter <= float(totMovies):\n' 
	cmd+='\tmidcounter=0\n'
	cmd+='\twhile midcounter < float(bufferMovie):\n'
        cmd+='\t\tmovie=linecache.getline(instanceList,counter+midcounter).split()[0]\n'
	cmd+='\t\tcmd="aws s3 cp s3://%s/%s ." %(s3,movie)\n'
        cmd+='\t\tsubprocess.Popen(cmd,shell=True)\n'
	cmd+='\t\tmidcounter=midcounter+1\n'
	cmd+='\tcounter=counter+midcounter\n'

        if os.path.exists('%s/downloadscript.py' %(homepath)):
                os.remove('%s/downloadscript.py' %(homepath))

        o1=open('%s/downloadscript.py' %(homepath),'w')
        o1.write(cmd)
        o1.close()
        
        return '%s/downloadscript.py' %(homepath)

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
        nProcsPerInstance=3

    homepath=subprocess.Popen('echo $HOME',shell=True, stdout=subprocess.PIPE).stdout.read().strip() 
    #Check if fabric is installed
    fabric_test=module_exists('fabric.api')
    if fabric_test is False:
	print 'Error: Could not find fabric installed and it is required. Install from here: http://www.fabfile.org/installing.html'
	sys.exit()
    #Import Fabric modules now: 
    from fabric.operations import run, put
    from fabric.api import env,run,hide,settings
    from fabric.context_managers import shell_env
    from fabric.operations import put
    crypto_test=module_exists('cryptography')
    if crypto_test is False: 
	print 'Error: Could not find cryptography python package. Install from here and try again: http://docs.python-guide.org/en/latest/scenarios/crypto/'
	sys.exit()
    from cryptography.fernet import Fernet
    r1='%s/tmp_%s.txt' %(homepath,''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(13)))
    r2='%s/tmp_%s.txt' %(homepath,''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(13)))
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)	
    key2=Fernet.generate_key()
    key3=Fernet.generate_key()
    #Need to create directory for AMIs across regions. Right now, just US-East-1 
    keyName,keyPath,AMI,region=checkConflicts(params,instanceType)

    ###################################    
    #Get number of movies in S3 bucket, then calculate number of instances needed to process in under an hour
    ###################################
    #>>> if calc num exceeds limit, use limit. 
    if os.path.exists('%s/s3listtmp55555.txt'%(homepath)): 
	os.remove('%s/s3listtmp55555.txt'%(homepath))
    	#Get home path
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

    #############################################
    ##Create lists of movies to run per instance#
    #############################################

    instanceCounter=1
    numMoviesPerInstance=math.ceil(num/numInstances)
    movieCounter=0
    while instanceCounter <= numInstances: 
	instancelist='%s/instance_list_4455992_%i.txt' %(homepath,instanceCounter)
	if os.path.exists(instancelist):
		os.remove(instancelist)
	o1=open(instancelist,'w')
	while movieCounter < numMoviesPerInstance*instanceCounter:
		o1.write('%s\n' %(movielist[movieCounter]))
		if params['debug'] is True:
			print movielist[movieCounter]
  		movieCounter=movieCounter+1
	instanceCounter=instanceCounter+1
	o1.close()

    #################################################
    #Transfer each movie list to separate instance###
    #################################################
    instanceCounter=1
    print instanceDict.keys()
    print instanceDict.keys()[0]

    print '\nSetting up virtual machines to align movies...\n'

    AWS_ACCESS_KEY_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_SECRET_ACCESS_KEY=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_ACCOUNT_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    AWS_DEFAULT_REGION=subprocess.Popen('echo $AWS_DEFAULT_REGION',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

    if os.path.exists(r1):
	os.remove(r1)
    owrite=open(r1,'w')
    owrite.write('%s\n' %(cipher_suite.encrypt(b'%s'%(AWS_ACCESS_KEY_ID))))
    owrite.write('%s\n' %(cipher_suite.encrypt(b'%s'%(AWS_SECRET_ACCESS_KEY))))
    owrite.write('%s\n' %(cipher_suite.encrypt(b'%s'%(AWS_ACCOUNT_ID))))
    owrite.write('%s\n' %(cipher_suite.encrypt(b'%s'%(AWS_DEFAULT_REGION))))
    owrite.close()
    if os.path.exists(r2):
	os.remove(r2)
    owrite=open(r2,'w')
    owrite.write('%s\n'%key2)
    owrite.write('%s\n'%key)
    owrite.write('%s\n'%key3)
    owrite.close()

    downloadscript=writeDownloadScript(homepath)
    splitscript=writeDivideScript(homepath)

    while instanceCounter <= numInstances:
	cmd='scp -o "StrictHostKeyChecking no" -i %s %s ubuntu@%s:~/' %(keyPath,r2,(instanceDict[instanceDict.keys()[instanceCounter-1]]))
    	subprocess.Popen(cmd,shell=True).wait()
	 
        cmd='scp -i %s %s ubuntu@%s:~/' %(keyPath,r1,(instanceDict[instanceDict.keys()[instanceCounter-1]]))
        if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()

	cmd='scp -i %s %s ubuntu@%s:~/' %(keyPath,downloadscript,(instanceDict[instanceDict.keys()[instanceCounter-1]]))
        if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()
 
	cmd='scp -i %s %s ubuntu@%s:~/' %(keyPath,splitscript,(instanceDict[instanceDict.keys()[instanceCounter-1]]))
        if params['debug'] is True:
                print cmd
        subprocess.Popen(cmd,shell=True).wait()

	instancelist='%s/instance_list_4455992_%i.txt' %(homepath,instanceCounter)
	
	cmd='aws s3 cp %s s3://%s/instance_list_4455992_%i.txt' %(instancelist,params['s3'],instanceCounter)
	if params['debug'] is True:
		print cmd
	subprocess.Popen(cmd,shell=True).wait()

	env.host_string='ubuntu@%s' %(instanceDict[instanceDict.keys()[instanceCounter-1]])
	env.key_filename = '%s' %(keyPath)

	awsInstallTest = exec_remote_cmd('which aws')
	if awsInstallTest.failed:
    		awsinstall = exec_remote_cmd('sudo apt-get install awscli -y')
    	if awsinstall.failed:
        	sys.exit()
	instanceCounter=instanceCounter+1 

    instanceListFileBasename='instance_list_4455992'

    print instanceDict 
    #totalThreads=numInstances*nProcsPerInstance 
    #Thread is defined as one 'group' of jobs
    #thread=1

    instanceCounter=1
    while instanceCounter <= numInstances:
		
		env.host_string='ubuntu@%s' %(instanceDict[instanceDict.keys()[instanceCounter-1]])
	        env.key_filename = '%s' %(keyPath)

		#parse encrypted keys
		i=1
		while i <= len(exec_remote_cmd('ls ~/tmp_*').split()):
		    tmpfile=exec_remote_cmd('ls ~/tmp_*').split()[i-1].split()[0] 
		    line=exec_remote_cmd('cat %s' %(tmpfile)).split()[0]
		    if len(line) <= 50:
		        r1=exec_remote_cmd('cat %s' %(tmpfile)).split()[1]
		        r1file=tmpfile
		    if len(line) >44:
		        r2=tmpfile
		    i=i+1
			
		cipher_suite = Fernet(r1)
		AWSSID=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[0])
		AWSSECRET=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[1])
		AWSACCOUNT=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[2])
		AWSREGION=cipher_suite.decrypt(exec_remote_cmd('cat %s' %(r2)).split()[3])

		with shell_env(AWS_ACCESS_KEY_ID=AWSSID,AWS_SECRET_ACCESS_KEY=AWSSECRET,AWS_ACCOUNT_ID=AWSACCOUNT,AWS_DEFAULT_REGION=AWSREGION):
			cp_result=exec_remote_cmd('aws s3 cp s3://%s/%s_%i.txt ~/' %(params['s3'],instanceListFileBasename,instanceCounter))
		        if cp_result.failed:
		               print 'Error: movie list copy failed.'
			print 'aws s3 cp s3://%s/%s_%i.txt ~/' %(params['s3'],instanceListFileBasename,instanceCounter)
                instanceCounter=instanceCounter+1

'''
    #Fabric copying: http://stackoverflow.com/questions/5314711/how-do-i-copy-a-directory-to-a-remote-machine-using-fabric

    ###########
    #Cleanup###
    ###########
    if params['debug'] is False:
    	instanceCounter=1
        os.remove(r1)
	os.remove(r2)
    	while instanceCounter <= numInstances:
        	instancelist='%s/instance_list_4455992_%i.txt' %(homepath,instanceCounter)
        	if os.path.exists(instancelist):
                	os.remove(instancelist)
		instanceCounter=instanceCounter+1
'''	
