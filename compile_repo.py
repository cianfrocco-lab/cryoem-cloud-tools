#!/usr/bin/env python
import shutil
import glob
import os
import subprocess

notincluded=['aws_init.sh','rclone','rclone_mac','aws_init.sh']

filelist=glob.glob('aws/*')

for f in filelist: 
	if f.split('/')[-1] in notincluded: 
		continue

	cmd='pyinstaller %s --onefile' %(f)
	print cmd
	subprocess.Popen(cmd,shell=True).wait()
	f1=f.split('/')[-1]
	if f1[-2:] == 'py': 
		cmd='mv dist/%s aws_build_osx/%s' %(f1[:-3],f1)
		print cmd
		subprocess.Popen(cmd,shell=True).wait()
	else:
		cmd='mv dist/%s aws_build_osx/%s' %(f1,f1)
		print cmd
                subprocess.Popen(cmd,shell=True).wait()

	os.remove('%s.spec' %(f1.split('.')[0]))

cmd='pyinstaller relion/qsub_aws --onefile'
subprocess.Popen(cmd,shell=True).wait()

cmd='mv dist/qsub_aws aws_build_osx/'
subprocess.Popen(cmd,shell=True).wait()

os.remove('qsub_aws.spec')
shutil.rmtree('dist')
shutil.rmtree('build')
