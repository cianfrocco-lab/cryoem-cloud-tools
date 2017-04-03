#!/usr/bin/env python

import os 
import subprocess
import sys 
import datetime
import time

keypair=sys.argv[1]
userIP=sys.argv[2]
outdir=sys.argv[3]
numstructures=sys.argv[4]
outfile=sys.argv[5]

now=datetime.datetime.now()
startday=now.day
starthr=now.hour
startmin=now.minute

cmd='echo "Starting Rosetta refinement on AWS on %s" >> %s' %(time.asctime(time.localtime(time.time())),outfile)



