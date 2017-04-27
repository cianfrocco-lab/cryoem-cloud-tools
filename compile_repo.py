#!/usr/bin/env python
import shutil
import glob
import os
import subprocess

notincluded=['aws_init.sh','rclone','rclone_mac','aws_init.sh','s3tmpout.txt']
outdirname='aws_build_linux' #Choices: aws_build_linux, aws_build_osx
filelist=glob.glob('aws/*')

for f in filelist: 
	if f.split('/')[-1] in notincluded: 
		continue

	cmd='pyinstaller %s --onefile' %(f)
	print cmd
	subprocess.Popen(cmd,shell=True).wait()
	f1=f.split('/')[-1]
	if f1[-2:] == 'py': 
		cmd='mv dist/%s %s/%s' %(f1[:-3],outdirname,f1)
		print cmd
		subprocess.Popen(cmd,shell=True).wait()
	else:
		cmd='mv dist/%s %s/%s' %(f1,outdirname,f1)
		print cmd
                subprocess.Popen(cmd,shell=True).wait()

	os.remove('%s.spec' %(f1.split('.')[0]))

cmd='pyinstaller relion/qsub_aws --onefile'
subprocess.Popen(cmd,shell=True).wait()

cmd='mv dist/qsub_aws %s/' %(outdirname)
subprocess.Popen(cmd,shell=True).wait()
os.remove('qsub_aws.spec')

if os.path.exists('install_cloud_tools'):
	os.remove('install_cloud_tools')
cmd='pyinstaller install_cloud_tools.py --onefile'
subprocess.Popen(cmd,shell=True).wait()
os.remove('install_cloud_tools.spec')

if outdirname == 'aws_build_linux':  
	cmd='mv dist/install_cloud_tools install_cloud_tools_Linux'
	subprocess.Popen(cmd,shell=True).wait()

shutil.rmtree('dist')
shutil.rmtree('build')
