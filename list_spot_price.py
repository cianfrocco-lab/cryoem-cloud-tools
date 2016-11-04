#!/usr/bin/env python
import time
import subprocess
import os
import sys 
if len(sys.argv) < 3:
	print '\nUsage: aws_spot_price_history [instance type] [avail. zone]\n'
	print '\nSpecify instance type over which spot price history will be listed based upon availability zone\n'
	sys.exit()

instanceType=sys.argv[1]
AZ=sys.argv[2]

#List instances given a users tag
keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

if len(keyPath) == 0:
	print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
	sys.exit()

if keyPath.split('/')[-1].split('.')[-1] != 'pem':
	print '\nError: Keypair specified is invalid, it needs to have .pem extension. Found .%s extension instead. Exiting\n' %(keyPath.split('/')[-1].split('.')[-1])
	sys.exit()

tag=keyPath.split('/')[-1].split('.')[0]

today=time.strftime("%Y/%m/%d")
day=float(today.split('/')[-1])-1
if day < 1:
	day=28
	month=float(today.split('/')[1])-1
if day >= 1:
	month=float(today.split('/')[1])
startTime='%s/%02.f/%02.f' %(today.split('/')[0],month,day)
cmd='aws ec2 describe-spot-price-history --instance-types %s --start-time %s --output table --availability-zone %s --filters Name=product-description,Values=Linux/UNIX' %(instanceType,startTime,AZ)
print cmd
#subprocess.Popen(cmd,shell=True).wait()

	
