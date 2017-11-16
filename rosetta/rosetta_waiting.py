#!/usr/bin/env python

from operator import itemgetter
import pickle
import datetime
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
        parser.set_usage("This program will wait for a rosetta refinement to finish on AWS.")
        parser.add_option("--instanceIDlist",dest="instanceID",type="string",metavar="FILE",
                    help="Instance ID list (pickle dump)")
        parser.add_option("--instanceIPlist",dest="instanceIP",type="string",metavar="FILE",
                    help="Instance IP list (pickle dump)")
        parser.add_option("--numModels",dest="numModels",type="int",metavar="INT",
                    help="Total number of models in rosetta run")
	parser.add_option("--numPerInstance",dest="numPerInstance",type="int",metavar="Number",
                    help="Number of models per instance requested")
	parser.add_option("--outdir",dest='outdir',type="string",metavar='FILE',
		    help='Output directory')
	parser.add_option("--type",dest='type',type="string",metavar='FILE',
                    help='Rosetta refinement type: relax or cm')
	parser.add_option("--pdbfilename",dest='pdbfilename',type="string",metavar='FILE',
                    help='PDB filename for first entry in pdb_list')
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

#================================================
if __name__ == "__main__":

	params=setupParserOptions()
        startTime=datetime.datetime.utcnow()
	now=datetime.datetime.now()
	startday=now.day
        starthr=now.hour
        startmin=now.minute

        l='%s/rosetta.out' %(params['outdir'])

        cmd='echo '' >> %s' %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo 'Rosetta model refinement started at %sUTC' >> %s" %(startTime.strftime('%Y-%m-%dT%H:%M:00'),l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo '' >> %s" %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo 'Checking job completion status (updates every 5 minutes)' >> %s" %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo '' >> %s" %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo 'Rosetta refinements typically take 1 - 6 hours' >> %s" %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd="echo '' >> %s" %(l)
        subprocess.Popen(cmd,shell=True).wait()

        keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	time.sleep(60)
	loadMin=5
	#Read in pickle files
	with open (params['instanceIP'], 'rb') as fp:
		instanceIPlist = pickle.load(fp)
	with open (params['instanceID'], 'rb') as fp:
                instanceIDlist = pickle.load(fp)

	os.makedirs('%s/output' %(params['outdir']))

	counter=0
	instanceCounter=1
	while counter < len(instanceIPlist):
	        isdone=0
        	while isdone == 0:
                	#If cloudwatch has load < 5% BUT there aren't finished PDBs yet, job crashed. Terminate.
	                time.sleep(300)
			currentTime=datetime.datetime.utcnow()
        	        if os.path.exists('%s/cloudwatchtmp.log'%(params['outdir'])):
                	        os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
	                cmd='aws cloudwatch get-metric-statistics --metric-name CPUUtilization --start-time %s  --period 300 --namespace AWS/EC2 --statistics Average --dimensions Name=InstanceId,Value=%s --end-time %s > %s/cloudwatchtmp.log' %(startTime.strftime('%Y-%m-%dT%H:%M:00'),instanceIDlist[counter],currentTime.strftime('%Y-%m-%dT%H:%M:00'),params['outdir'])
        	        subprocess.Popen(cmd,shell=True).wait()
                	o1=open('%s/cloudwatchtmp.log'%(params['outdir']),'r')
			testflag=0
	                for line in o1:
        	                if len(line.split())>0:
                	                if line.split()[0] == '"Average":':
                        	                load=float(line.split()[1][:-1])
						if load >= loadMin: 
							if testflag==0: 
								cmd='echo "...running...   (%sUTC)" >> %s' %(currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
								subprocess.Popen(cmd,shell=True).wait()
								testflag=1
								cmd='echo "" >> %s' %(l)
                                                                subprocess.Popen(cmd,shell=True).wait()

						if load < loadMin:
							#Download all pdb files, take note if you didn't download enough files consdiering number of models requested
	                                                isdone=1
							testflag=1
							cmd='echo "Job finished on #%i at %sUTC" >> %s' %(counter+1,currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
							subprocess.Popen(cmd,shell=True).wait()
							cmd='echo "Transferring PDB and score files into output directory" >> %s' %(l)
                                                        subprocess.Popen(cmd,shell=True).wait()
        						currCounter=1				
							while currCounter <= params['numPerInstance']:
								if params['type'] == 'cm':
									cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/S_%i_0001.pdb %s/output/S_%i_0001.pdb' %(keypair,instanceIPlist[counter],currCounter,params['outdir'],instanceCounter)
									subprocess.Popen(cmd,shell=True).wait()
								if params['type'] == 'relax':
                                                                        cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/%s_%i_0001.pdb %s/output/S_%i_0001.pdb' %(keypair,instanceIPlist[counter],params['pdbfilename'][:-4],currCounter,params['outdir'],instanceCounter)
                                                                        subprocess.Popen(cmd,shell=True).wait()

								cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ubuntu@%s:~/score_%i.sc %s/output/S_%i_0001_score.sc' %(keypair,instanceIPlist[counter],currCounter,params['outdir'],instanceCounter)
								subprocess.Popen(cmd,shell=True).wait()
								instanceCounter=instanceCounter+1
								currCounter=currCounter+1	

							cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceIDlist[counter],params['outdir'])
        						subprocess.Popen(cmd,shell=True).wait()

		        o1.close()
                	os.remove('%s/cloudwatchtmp.log'%(params['outdir']))
		counter=counter+1

        cmd='echo "Rosetta refinement finished. Shutting down instances at %sUTC" >> %s' %(currentTime.strftime('%Y-%m-%dT%H:%M:00'),l)
	subprocess.Popen(cmd,shell=True).wait()

	counter=0
	while counter < len(instanceIPlist):
        	isdone=0
        	while isdone == 0:
              		status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceIDlist[counter]),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
              		if status == 'terminated':
                    		isdone=1
              	time.sleep(10)
		counter=counter+1

        now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1

	listname = '%s/output/*.sc' %(params['outdir'])	
	f1 = glob.glob(listname)
        
	#Create output file
	outputsc = '%s/model_scores.txt' %(params['outdir'])

	#Open output box file for writing new lines
        outputsc_write = open(outputsc,'w')

	for sc in f1:

		#Generate the score file name, file number etc.
		splitSc = sc.split('/')
		file_name_with_ext = '%s' %(splitSc[-1])
                file_name = '%s' %(file_name_with_ext[:-9])

		#Open score file for reading
        	inputsc = open(sc,'r')
		counter = 1
		
		#Loop over all lines in the input scorefile
        	for line in inputsc:
			#Split line into values that were separated by tabs
                	splitLine = line.split()
		
                	if len(line.split()) > 2:
				if not splitLine[1] == 'total_score':

					#Write out the name of the pdb and the energr score
                    			outputsc_write.write('%s/output/%s.pdb\t%s\n' %(params['outdir'],file_name,splitLine[1]))
					counter = counter + 1

	outputsc_write.close()


	#Create sorted file
	sorted_outputsc = '%s_ranked.txt' %(outputsc[:-4])


	with open('%s' %(outputsc)) as fin:
		data =[]
		for line in fin:
			line = line.split()
			line[1] = float(line[1])
			data.append(line)


		data.sort(key=itemgetter(1))
		
		with open('%s' %(sorted_outputsc), 'w') as fout:
			for e1 in data:
				#e2 = str(e1)
				#fout.write ('{0}\n'.format('\t'.join(str(e1))))
				fout.write ('\t'.join('{}'.format(i) for i in e1))
				fout.write('\n')

	os.makedirs('%s/top_10_models' %(params['outdir']))

	maxcounter=10
	counter=1
	filenumlines=len(open(sorted_outputsc,'r').readlines())
	if filenumlines < maxcounter: 
		maxcounter=filenumlines
	while counter<=maxcounter: 
		modfile=linecache.getline(sorted_outputsc,counter).split()[0].strip()
		shutil.copyfile(modfile,'%s/top_10_models/%s' %(params['outdir'],modfile.split('/')[-1]))
		counter=counter+1

	badfiles=glob.glob('%s/aws*log' %(params['outdir']))
	for badfile in badfiles: 
		os.remove(badfile)
	if os.path.exists('%s/instanceIPlist.txt'%(params['outdir'])): 
		os.remove('%s/instanceIPlist.txt'%(params['outdir']))
	#if os.path.exists('%s/volIDlist.txt'%(params['outdir'])): 
	#	os.remove('%s/volIDlist.txt'%(params['outdir']))
	if os.path.exists('%s/instanceIDlist.txt' %(params['outdir'])): 
		os.remove('%s/instanceIDlist.txt' %(params['outdir']))
	if os.path.exists('%s/tmp4949585940.txt' %(params['outdir'])): 
		os.remove('%s/tmp4949585940.txt' %(params['outdir']))

	cmd='echo "" >> %s' %(l)
	subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "List of models and associated Rosetta score: %s/model_scores.txt" >> %s' %(params['outdir'],l)
	subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "" >> %s' %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd='echo "List of models ranked by score, best (lowest energy) to worst score: %s/model_scores_ranked.txt" >> %s' %(params['outdir'],l)
        subprocess.Popen(cmd,shell=True).wait()
	
	cmd='echo "" >> %s' %(l)
        subprocess.Popen(cmd,shell=True).wait()

        cmd='echo "Top 10 models with lowest energy can be found: %s/top_10_models/" >> %s' %(params['outdir'],l)
        subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "" >> %s' %(l)
        subprocess.Popen(cmd,shell=True).wait()
