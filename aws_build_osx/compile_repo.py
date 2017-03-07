#!/usr/bin/env python

import glob
import os
import subprocess

notincluded=['s3.log','aws_init.sh','rclone','rclone_mac','aws_init.sh']

filelist=glob.glob('aws/*')

for f in filelist: 
	if f.split('/')[-1] in notincluded: 
		continue
	cmd='pyinstaller %s --onefile' %(f)
	subprocess.Popen(cmd,shell=True).wait()

	
