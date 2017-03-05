#!/usr/bin/env python

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
        parser.set_usage("This program will submit a rosetta atomic model refinement to AWS for refinement. Specify input pdb file(s) and cryo-EM maps below.\n\n%prog --pdb_list=<.txt file with the list of input pdbs and their weights> --em_map=<EM map in .mrc format> --num=<number of atomic strucutres per CPU process (default:5)")
        parser.add_option("--pdb_list",dest="pdb_list",type="string",metavar="FILE",
                    help=".txt file with the input pdbs and their weights")
        parser.add_option("--em_map",dest="em_map",type="string",metavar="FILE",
                    help="EM map in .mrc format")
	parser.add_option("--AMI",dest="AMI",type="string",metavar="AMI",
                    help="AMI for Rosetta software environment on AWS. (Read more here: cryoem-tools.cloud/rosetta-aws)")
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

#=============================
def checkConflicts(params):

        if not os.path.exists(params['pdb_list']):
                print "\nError: input pdb list %s doesn't exists, exiting.\n" %(params['pdb_list'])
                sys.exit()
	if not os.path.exists(params['em_map']):
                print "\nError: input EM map list %s doesn't exists, exiting.\n" %(params['em_map'])
                sys.exit()      

	volsize=os.path.getsize(params['em_map'])/1000000

	if volsize >250: 
		print 'Error: Volume size is too large - did you try cutting out extra density to make a smaller volume?'
		sys.exit()

	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	if os.path.exists('hybridize_final.xml'): 
		print 'Error: Rosetta parameter file hybridize_final.xml already exists in current directory. Exiting.'
		sys.exit()
	if os.path.exists('run_final.sh'): 
		print 'Error: Rosetta refinement run parameter file run_final.sh already exists in current directory. Exiting.'
		sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        rosettadir=subprocess.Popen('echo $AWS_DIR',shell=True, stdout=subprocess.PIPE).stdout.read().split()[0] + '/rosetta'
	if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()
	
	if len(AWS_ID) == 0: 
		print 'Error: Could not find the environmental variable $AWS_ACCOUNT_ID. Exiting'
		sys.exit()
	if len(key_ID) == 0: 
		print 'Error: Could not find the environmental variable $AWS_ACCESS_KEY_ID. Exiting'
                sys.exit()
	if len(secret_ID) == 0:
		print 'Error: Could not find the environmental variable $AWS_SECRET_ACCESS_ID. Exiting'
                sys.exit()
	if len(teamname) == 0: 
		print 'Error: Could not find the environmental variable $RESEARCH_GROUP_NAME. Exiting'
                sys.exit()
	if len(keypair) == 0: 
		print 'Error: Could not find the environmental variable $KEYPAIR_PATH. Exiting'
                sys.exit()

	return awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir,volsize

#================================================
if __name__ == "__main__":

	##Hard coded values
	sizeneeded=100
	instance='t2.micro'

        params=setupParserOptions()
	awsregion,AWS_ID,key_ID,secret_ID,teamname,keypair,awsdir,rosettadir,volsize=checkConflicts(params)
	
	project=''
        #Get project name if exists
        if os.path.exists('.aws_relion_project_info'):
                project=linecache.getline('.aws_relion_project_info',1).split('=')[-1]

	#Prepare input files
	cmd='%s/rosetta_prepare_input_files.py --pdb_list=%s --em_map=%s'  %(rosettadir,params['pdb_list'],params['em_map'])
	subprocess.Popen(cmd,shell=True).wait()

	#Error check
	if not os.path.exists('run_final.sh'): 
		print 'Error: Rosetta file preparation failed, was unable to create run_final.sh. Exiting'
		sys.exit()
	if not os.path.exists('hybridize_final.xml'): 
		print 'Error: Rosetta file preparation failed, was unable to create hybridize_final.xml. Exiting'
		sys.exit()

	#Create EBS volume
	if os.path.exists('awsebs.log') :
        	os.remove('awsebs.log')
        cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%0.f"'%(awsdir,sizeneeded,awsregion,teamname,time.time())+'> awsebs.log'
        subprocess.Popen(cmd,shell=True).wait()
        ###Get volID from logfile
        volID=linecache.getline('awsebs.log',5).split('ID: ')[-1].split()[0]
        time.sleep(10)
        os.remove('awsebs.log')

	print '\nLaunching virtual machine %s on AWS in region %sa (initialization will take a few minutes)\n' %(instance,awsregion)

	#Launch instance
	if os.path.exists('awslog.log'):
	        os.remove('awslog.log')
        cmd='%s/launch_AWS_instance.py --instance=%s --availZone=%sa --volume=%s --AMI %s > awslog.log' %(awsdir,instance,awsregion,volID,params['AMI'])
        subprocess.Popen(cmd,shell=True)
        time.sleep(10)
        isdone=0
        qfile='awslog.log'
        while isdone == 0:
        	r1=open(qfile,'r')
                for line in r1:
                	if len(line.split()) == 2:
                        	if line.split()[0] == 'ID:':
                                        isdone=1
                r1.close()
                time.sleep(10)
        keypair=linecache.getline('awslog.log',16).split()[3].strip()
        userIP=linecache.getline('awslog.log' ,16).split('@')[-1].strip()
        instanceID=linecache.getline('awslog.log' ,18).split()[-1]
        os.remove('awslog.log')

        now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute

	#Upload data
	env.host_string='ubuntu@%s' %(userIP)
        dirlocation='/data'
	
	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s run_final.sh ubuntu@%s:~/'%(keypair,userIP)
        subprocess.Popen(cmd,shell=True).wait()

	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s hybridize_final.xml ubuntu@%s:~/'%(keypair,userIP)
        subprocess.Popen(cmd,shell=True).wait()

	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/' %(keypair,userIP,params['em_map'])
	subprocess.Popen(cmd,shell=True).wait()

	#Run job
	o2=open('run_aws.job','w')
        o2.write('./relion_movie_align.py %s_%i.star %i rclonename:%s/Micrographs %s %i %s "%s" "%s" %s %f %s' %(micstar[:-5],instanceNum,ntasks,bucketname.split('s3://')[-1],bucketname.split('s3://')[-1],ntasks*2,movieAlignType,relioncmd,gainref,outdir,angpix,savemovies))
        o2.close()
        st = os.stat('run_aws.job')
        os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
        cmd='rsync -q -avzu -e "ssh -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > rsync.log' %(keypair,userIP)
        subprocess.Popen(cmd,shell=True).wait()

        cmd='ssh  -o "StrictHostKeyChecking no" -q -n -f -i %s ubuntu@%s "export PATH=/home/EM_Packages/relion2.0/build/bin:$PATH && export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH && ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,IPlist[instanceNum],outdir,outdir)
        subprocess.Popen(cmd,shell=True)


	
