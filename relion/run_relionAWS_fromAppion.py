#!/usr/bin/env python
import glob
import time
import stat
import math
import linecache
import os
import sys
import subprocess
from fabric.operations import run, put
from fabric.api import env,run,hide,settings
from fabric.context_managers import shell_env
from fabric.operations import put
import shutil
import datetime

#==========================
def s3_to_ebs(IP,keypair,bucketname,dironebs,rclonepath,keyid,secretid,region,numfilesAtATime):
	#Copy rclone onto instance
	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/'%(keypair,rclonepath,IP)
	subprocess.Popen(cmd,shell=True).wait()

	#Write rclone config file
	homedir='/home/ubuntu/'
	rclonename='ebss3'
	if os.path.exists('.rclone.conf'):
		os.remove('.rclone.conf')
	r1=open('rclone.conf','w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(keyid))
        r1.write('secret_access_key = %s\n' %(secretid))
        r1.write('region = %s\n' %(region))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(region))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s rclone.conf ubuntu@%s:~/.rclone.conf' %(keypair,IP)
	subprocess.Popen(cmd,shell=True).wait()

	#Copy data down
	env.host_string='ubuntu@%s' %(IP)
        env.key_filename = '%s' %(keypair)
	rcloneexe='rclone'
	exec_remote_cmd('%s/%s copy rclonename:%s %s --max-size 1G --quiet --transfers %i' %(homedir,rcloneexe,bucketname.split('s3://')[-1],dironebs,numfilesAtATime))

	fileonly=dironebs.split('/')[-1]
	if dironebs.split('.')[-1] == 'mrcs' or dironebs.split('.')[-1] == 'spi': 
		exec_remote_cmd('mv %s/%s tmp.mrcs' %(dironebs,fileonly))
		exec_remote_cmd('rm -rf /%s/' %(dironebs))
		exec_remote_cmd('mv tmp.mrcs /data/%s' %(fileonly))
#==========================
def s3_to_ebs_movie(IP,keypair,bucketname,dironebs,rclonepath,keyid,secretid,region,numfilesAtATime):
        #Copy rclone onto instance
        cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:~/'%(keypair,rclonepath,IP)
        subprocess.Popen(cmd,shell=True).wait()

        #Write rclone config file
        homedir='/home/ubuntu/'
        rclonename='ebss3'
        if os.path.exists('.rclone.conf'):
                os.remove('.rclone.conf')
        r1=open('rclone.conf','w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(keyid))
        r1.write('secret_access_key = %s\n' %(secretid))
        r1.write('region = %s\n' %(region))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(region))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

        cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s rclone.conf ubuntu@%s:~/.rclone.conf' %(keypair,IP)
        subprocess.Popen(cmd,shell=True).wait()

        #Copy data down
        env.host_string='ubuntu@%s' %(IP)
        env.key_filename = '%s' %(keypair)
        rcloneexe='rclone'
        exec_remote_cmd('%s/%s copy rclonename:%s %s --min-size 500M --quiet --transfers %i' %(homedir,rcloneexe,bucketname.split('s3://')[-1],dironebs,numfilesAtATime))

        fileonly=dironebs.split('/')[-1]
        if dironebs.split('.')[-1] == 'mrcs' or dironebs.split('.')[-1] == 'spi':
                exec_remote_cmd('mv %s/%s tmp.mrcs' %(dironebs,fileonly))
                exec_remote_cmd('rm -rf /%s/' %(dironebs))
                exec_remote_cmd('mv tmp.mrcs /data/%s' %(fileonly))


#=========================
def rclone_to_s3_mics(micstar,numfiles,region,keyid,secretid,rclonename,bucketname,awspath,project):

	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
		rclonepath='%s/rclone' %(awspath)
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		rclonepath='%s/rclone_mac'%(awspath)

        #Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if os.path.exists('%s/.rclone.conf' %(homedir)):
                os.remove('%s/.rclone.conf' %(homedir))

        r1=open('%s/.rclone.conf' %(homedir),'w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(keyid))
        r1.write('secret_access_key = %s\n' %(secretid))
        r1.write('region = %s\n' %(region))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(region))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

	directoryToTransfer=micstar.split('/')
	del directoryToTransfer[-1]
	directoryToTransfer='/'.join(directoryToTransfer)

	#Check first micro to see if it is in directoryToTransfer
	#Get column number first
	o1=open(micstar,'r')
	for line in o1: 
		if len(line.split())> 0: 
			if line.split()[0]=='_rlnMicrographName': 
				micolnum=line.split()[1].split('#')[-1]
	o1.close()
	o1=open(micstar,'r')
	flag=0
	for line in o1:
		if len(line.split())> 0:
        		if os.path.exists(line.split()[int(micolnum)-1]):
				if flag == 0:
					path=line.split()[int(micolnum)-1].split('/')
					del path[-1]
					path='/'.join(path)
					flag=1
	o1.close()
	cmd='%s copy %s rclonename:%s --quiet   --transfers %i > rclone.log' %(rclonepath,directoryToTransfer,bucketname,math.ceil(numfiles))
	subprocess.Popen(cmd,shell=True).wait()
	otherbucket=''
	if path != directoryToTransfer:

		#Get uploadlist
		o13=open('uploadlist.txt','w')
		for line in open(micstar,'r'):
			if len(line.split()) > 0:
				if os.path.exists(line.split()[int(micolnum)-1]):
					o13.write('%s\n' %(line.split()[int(micolnum)-1].split('/')[-1]))
		o13.close()
		cmd='%s copy %s/ rclonename:%s-mic --include-from uploadlist.txt --quiet --transfers %i > rclone.log' %(rclonepath,path,bucketname,math.ceil(numfiles))
		subprocess.Popen(cmd,shell=True).wait()

		otherbucket='%s-mic' %(bucketname)
		os.remove('uploadlist.txt')

	os.remove('rclone.log')
	return 's3://%s' %(bucketname),directoryToTransfer,'s3://%s' %(otherbucket),path

#=========================
def rclone_to_s3_movie(micstar,numfiles,region,keyid,secretid,rclonename,bucketname,awspath,project):

	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
		rclonepath='%s/rclone' %(awspath)
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		rclonepath='%s/rclone_mac'%(awspath)

        #Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if os.path.exists('%s/.rclone.conf' %(homedir)):
                os.remove('%s/.rclone.conf' %(homedir))

        r1=open('%s/.rclone.conf' %(homedir),'w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(keyid))
        r1.write('secret_access_key = %s\n' %(secretid))
        r1.write('region = %s\n' %(region))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(region))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

	#Find which directory has the micrographs for transferring
        for line in open(micstar,'r'):
                if len(line) < 40:
			if len(line.split()) >= 1:
				if line.split()[0] == '_rlnMicrographMovieName':
					if len(line.split()) == 1:
						microcol = 1
					if len(line.split()) == 2:
                                        	microcol=int(line.split()[1].split('#')[-1])
	o22=open('micinclude.txt','w')
        symflag=0
        samedir=0
        for line in open(micstar,'r'):
                if len(line) == 0:
                        continue
		if line[0] == '_':
			continue
                if line[-1] == '_':
			continue
		if len(line.split()[microcol-1].split('/')) == 0:
                        dirtransfer=''
                        origdir=''
                        samedir=1
                        mic=line.split()[microcol-1]
                        miconly=mic.split('/')[-1]
                        o22.write('%s\n' %(miconly))
                if len(line.split()[microcol-1].split('/')) > 0:
                        mic=line.split()[microcol-1]
                        miconly=mic.split('/')[-1]
                        origdir=mic.split(miconly)[0]
                        if os.path.islink(mic) is True:
				symdir=os.path.realpath(mic).split(miconly)[0]
                                dirtransfer=symdir
                                o22.write('%s\n' %(miconly))
                                symflag=1
                        if os.path.islink(mic) is False:
				dirtransfer=line.split()[microcol-1].split('/')[0]
        o22.close()
        #Create bucket on aws:
        #if len(project) == 0:
	#	cmd='aws s3 mb s3://%s --region %s > s3.log' %(bucketname,region)
	#	subprocess.Popen(cmd,shell=True).wait()
        #	os.remove('s3.log')
	#if len(project) > 0:
	#	cmd='touch .tmp'
	#	subprocess.Popen(cmd,shell=True).wait()
	#	cmd='aws s3 cp .tmp s3://%s/ --region %s > s3.log' %(bucketname,region)
	#	subprocess.Popen(cmd,shell=True).wait()
	#	os.remove('.tmp')
	#	os.remove('s3.log')

        if len(dirtransfer)>0:
                if symflag == 0:
                        cmd='%s copy %s rclonename:%s/ --quiet   --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
			subprocess.Popen(cmd,shell=True).wait()
                        os.remove('rclone.log')
                if symflag == 1:
                        cmd='%s copy %s rclonename:%s --include-from micinclude.txt --quiet --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
			subprocess.Popen(cmd,shell=True).wait()
                        os.remove('rclone.log')
        if len(dirtransfer) == 0:
                cmd='%s copy . rclonename:%s --include-from micinclude.txt --quiet  --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
		subprocess.Popen(cmd,shell=True).wait()
                os.remove('rclone.log')
        if os.path.exists('micinclude.txt'):
		os.remove('micinclude.txt')
	return 's3://%s' %(bucketname),dirtransfer,origdir

#=========================
def rclone_to_s3_preprocess(micstar,numfiles,region,keyid,secretid,rclonename,bucketname,awspath,project):

	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
		rclonepath='%s/rclone' %(awspath)
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		rclonepath='%s/rclone_mac'%(awspath)

        #Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if os.path.exists('%s/.rclone.conf' %(homedir)):
                os.remove('%s/.rclone.conf' %(homedir))

        r1=open('%s/.rclone.conf' %(homedir),'w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(keyid))
        r1.write('secret_access_key = %s\n' %(secretid))
        r1.write('region = %s\n' %(region))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(region))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

	microcol=1
	o22=open('micinclude.txt','w')
	symflag=0
	samedir=0
	for line in open(micstar,'r'):
		if len(line) < 40:
			continue
		if len(line.split()[microcol-1].split('/')) == 0:
			dirtransfer=''
			origdir=''
			samedir=1
			mic=line.split()[microcol-1]
			miconly=mic.split('/')[-1]
			o22.write('%s\n' %(miconly))
		if len(line.split()[microcol-1].split('/')) > 0:
			mic=line.split()[microcol-1]
			miconly=mic.split('/')[-1]
			origdir=mic.split(miconly)[0]
			if os.path.islink(mic) is True:
				symdir=os.path.realpath(mic).split(miconly)[0]
				dirtransfer=symdir
				o22.write('%s\n' %(miconly))
				symflag=1
			if os.path.islink(mic) is False:
				dirtransfer=line.split()[microcol-1].split(miconly)[0]
				
	o22.close()

	if len(dirtransfer)>0:
		if symflag == 0:
			cmd='%s copy %s rclonename:%s --quiet --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
			subprocess.Popen(cmd,shell=True).wait()
        		os.remove('rclone.log')
		if symflag == 1:
			cmd='%s copy %s rclonename:%s --quiet --include-from micinclude.txt --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
			subprocess.Popen(cmd,shell=True).wait()
			os.remove('rclone.log')
        if len(dirtransfer) == 0:
		cmd='%s copy . rclonename:%s --quiet --include-from micinclude.txt --transfers %i > rclone.log' %(rclonepath,dirtransfer,bucketname,math.ceil(numfiles))
                subprocess.Popen(cmd,shell=True).wait()
                os.remove('rclone.log')
	return 's3://%s' %(bucketname),dirtransfer,origdir

#=========================
def rclone_to_s3(indir,numfiles,region,keyid,secretid,rclonename,bucketname,awspath,project,rclonelist):
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
		rclonepath='%s/rclone' %(awspath)
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		rclonepath='%s/rclone_mac'%(awspath)

	#Write .rclone.conf
	homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if os.path.exists('%s/.rclone.conf' %(homedir)):
		os.remove('%s/.rclone.conf' %(homedir))

	r1=open('%s/.rclone.conf' %(homedir),'w')
	r1.write('[rclonename]\n')
	r1.write('type = s3\n')
	r1.write('env_auth = false\n')
	r1.write('access_key_id = %s\n' %(keyid))
	r1.write('secret_access_key = %s\n' %(secretid))
	r1.write('region = %s\n' %(region))
	r1.write('endpoint = \n')
	r1.write('location_constraint = %s\n' %(region))
	r1.write('acl = authenticated-read\n')
	r1.write('server_side_encryption = \n')
	r1.write('storage_class = STANDARD\n')
	r1.close()

	#Create bucket on aws:
	#if len(project) == 0: 
	#	cmd='aws s3 mb s3://%s --region %s > s3.log' %(bucketname,region)
	#	subprocess.Popen(cmd,shell=True).wait()
	#	os.remove('s3.log')
	if len(rclonelist) == 0: 
		cmd='%s copy %s rclonename:%s --quiet --transfers %i > rclone.log' %(rclonepath,indir,bucketname,math.ceil(numfiles))
		subprocess.Popen(cmd,shell=True).wait()
	if len(rclonelist) > 0: 
		cmd='%s copy %s rclonename:%s --quiet --transfers %i --include-from %s > rclone.log' %(rclonepath,indir,bucketname,math.ceil(numfiles),rclonelist)
		subprocess.Popen(cmd,shell=True).wait()
	os.remove('rclone.log')
	return 's3://%s' %(bucketname)

#=========================
def parallel_rsync(indir,threads,keypair,IP,destdir):
	inlist=glob.glob('%s/*' %(indir))
	microlist=[]
	for entry in inlist:
		if os.path.isdir(entry):
			microlist.append(entry)
			inlist.remove(entry)

	if len(microlist)>0:
		counter=0
		while counter < len(microlist):
			testlist=glob.glob('%s/*' %(microlist[counter]))
			for test in testlist:
				if os.path.isfile(test):
					inlist.append(test)
			counter=counter+1
	numpergroup=math.ceil(len(inlist)/threads)
	threadcounter =0
	miccounter=0
	while threadcounter < threads:
		if os.path.exists('rsync_thread%i.txt' %(threadcounter)):
			os.remove('rsync_thread%i.txt' %(threadcounter))
		o1=open('rsync_thread%i.txt' %(threadcounter),'w')
		while miccounter < (threadcounter*numpergroup+numpergroup):
			o1.write('%s\n' %(inlist[miccounter].strip()))
			miccounter=miccounter+1
		threadcounter=threadcounter+1
	last=threads-1
	threadcounter=0
	while threadcounter < threads:
		if os.path.exists('rsync_thread%i_log.txt' %(threadcounter)):
			os.remove('rsync_thread%i_log.txt' %(threadcounter))
		cmd='rsync --ignore-errors -R -avzu -e "ssh -o StrictHostKeyChecking=no -i %s" `cat rsync_thread%i.txt`  ubuntu@%s:%s > rsync_thread%i_log.txt' %(keypair,threadcounter,IP,destdir,threadcounter)
		subprocess.Popen(cmd,shell=True)
		threadcounter=threadcounter+1

	threadcounter=0
	while threadcounter < threads:
		if os.path.exists('rsync_thread%i_log.txt' %(threadcounter)):
			check=subprocess.Popen('cat rsync_thread%i_log.txt | grep sent' %(threadcounter),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
			if len(check) > 0:
				os.remove('rsync_thread%i_log.txt' %(threadcounter))
				threadcounter=threadcounter+1

	cmd='rsync -R --ignore-errors -avzu -e "ssh -o StrictHostKeyChecking=no -i %s" %s/ ubuntu@%s:%s/ > rsync.log' %(keypair,indir,IP,destdir)
        subprocess.Popen(cmd,shell=True).wait()
	os.remove('rsync.log')

#====================
def exec_remote_cmd(cmd):
    from fabric.operations import run, put
    from fabric.api import hide,settings
    with hide('output','running','warnings'), settings(warn_only=True):
    	return run(cmd)

#==============================
def writeToLog(msg,outfile):
	cmd='echo '' >> %s' %(outfile)
	subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "%s"  >> %s' %(msg,outfile)
        subprocess.Popen(cmd,shell=True).wait()

#==============================
def getJobType(f1):
	jobtype='None'
	o1=open(f1,'r')
        flag=0
	'''
	for line in o1:
                if flag == 0:
			if len(line.split('=')) > 0:
                        	if line.split('=')[0] == 'relioncmd':
                                	rlncmd=line.split('=')[1]
					flag=1
        o1.close()
	return rlncmd.split('`')[1].split('which')[-1].strip()
	'''
	rlncmdlist=[]
	for line in o1:
                if len(line)>0:
			if len(line.split('=')) > 0:
                                if line.split('=')[0] == 'relioncmd':
					if 'which' in line: 
						rlncmd=line.split('=')[1]
                                        	rlncmdlist.append(rlncmd.split('`')[1].split('which')[-1].strip())
	return rlncmdlist[0],len(rlncmdlist)
	
#==============================
def getCMDrefine(f1):
	o1=open(f1,'r')
	for line in o1:
		if len(line.split('=')) > 0:
			if line.split('=')[0] == 'relioncmd':
				rlncmd=line.split('=')[1]
	o1.close()

	#Get particle input directory and if there is a reference model
	outbasenanme=''
	continuecounter=-1
	indircounter=-1
	refcounter=-1
	outcounter=-1
	autoref=-1
	counter=1
	itercounter=0
	numiters=0
	mask=''
	maskcounter=-1
	ref='None'
	stack=False
	partstarname=''
	partdir=''
	contLocation=''
	particlediameter=-999
	partdiamcounter=-1
	for l in rlncmd.split():
		if l == '--i':
			indircounter=counter
		if l == '--ref':
			refcounter=counter
		if l == '--o':
			outcounter=counter
		if l == '--auto_refine':
			autoref=counter
		if l == '--iter': 
			itercounter=counter
		if l == '--solvent_mask': 
			maskcounter=counter
		if l == '--continue':
			continuecounter=counter
		if l == '--particle_diameter':
			partdiamcounter=counter
		counter=counter+1

	if indircounter > 0: 
		partstarname=rlncmd.split()[indircounter].split('/')[-1]
		if '.star' not in partstarname: 
			stack=True
		partdir=rlncmd.split()[indircounter].split('/')
		del partdir[-1]
		partdir='/'.join(partdir)
	if partdiamcounter > 0: 
		particlediameter=float(rlncmd.split()[partdiamcounter])
	outbasename=rlncmd.split()[outcounter]
	outdir=rlncmd.split()[outcounter].split('/')
	del outdir[-1]
	outdir='/'.join(outdir)
	if itercounter > 0:
		numiters=int(rlncmd.split()[itercounter])
	if refcounter > 0:
		ref=rlncmd.split()[refcounter]
	if maskcounter > 0: 
		mask=rlncmd.split()[maskcounter]
	if continuecounter > 0: 
		contLocation=rlncmd.split()[continuecounter]
	return rlncmd,partdir,ref,outdir,autoref,numiters,partstarname,mask,stack,contLocation,outbasename,particlediameter

#==============================
def checkPartLocation(instarfile,indir): 

	otherPartDir=''
	otherPartRclone=[]
	error=''

	o44=open(instarfile,'r')
	for line in o44: 
		if len(line) > 0: 
			if 'data' not in line: 
				if '_rln' in line: 
					if line.split()[0] == '_rlnImageName': 
						imagecolnum=int(line.split('#')[-1])
					if line.split()[0] == '_rlnMicrographName':
						microcolnum=int(line.split('#')[-1])
	o44.close()					

	if microcolnum == 0: 
		error='Could not find _rlnImageName in starfile %s' %(instarfile)
	if microcolnum != 0: 
		o44=open(instarfile,'r')
		for line in o44:	
			if len(line.split()) > 0: 
				if 'data' not in line: 
					if '_rln' not in line: 
						if 'loop_' not in line:
							part=line.split()[imagecolnum-1].split('@')[-1]
							starfile=''
							if not os.path.exists(part): 
								error='Error: particle stack %s does not exist.' %(part)
							if os.path.exists('%s_extract.star' %(part[:-5])): 
								starfile='%s_extract.star' %(part[:-5])
							InIt=False
							if indir in part: 
								InIt=True
							if InIt is False:
								if len(part.split('/')) == 5:
									otherPartDir=part.split('/')[0]+'/'+part.split('/')[1]+'/'
									tmpline=part.split('/')[2]+'/'+part.split('/')[3]+'/'+part.split('/')[4]
									tmpline=tmpline.replace('//','/')
									otherPartRclone.append(tmpline)
								if len(part.split('/')) == 4: 
									otherPartDir=part.split('/')[0]+'/'+part.split('/')[1]+'/'
									otherPartRclone.append(part.split('/')[2]+'/'+part.split('/')[3])
								if len(part.split('/')) == 3: 
									otherPartDir=part.split('/')[0]+'/'+part.split('/')[1]+'/'
                                                                        otherPartRclone.append(part.split('/')[2])
							'''
							checkdir=part.split(micro)[0]
							if checkdir[-1] == '/': 
								checkdir=checkdir[:-1]
							if checkdir != indir: 
								otherPartDir=checkdir	
								if micro not in otherPartRclone: 
									partfilename=part.split('/')[-1]
									micdironly=micro.split('/')
									del micdironly[-1]
									micdironly='/'.join(micdironly)
									otherPartRclone.append('%s/%s' %(micdironly,partfilename))
									if len(starfile) > 0: 
										instarfile='%s/%s_extract.star' %(micdironly,partfilename[:-5])
										if instarfile not in otherPartRclone:
											otherPartRclone.append(instarfile)
							'''
		o44.close()
	return otherPartDir,otherPartRclone,error

#==============================
def parseCMDrefine(relioncmd):

	l=relioncmd.split()
	newcmd=[]
	tot=len(l)
	counter=0
	selectflag=''
	while counter < tot:
		if l[counter] == '--preread_images':
			counter=counter+1
			continue
		if l[counter] == '--pool':
			counter=counter+2
			continue
		if l[counter] == '`which':
			counter=counter+1
			continue
		if l[counter] == 'relion_refine_mpi`':
			counter=counter+1
			continue
		if l[counter] == 'relion_refine`':
                        counter=counter+1
                        continue
		if l[counter] == '--gpu':
			if counter+1 < tot: 
				if l[counter+1][0] == '-': 
					counter=counter+1
				else:
					counter=counter+2
			else: 
				counter=counter+1
			continue
		if l[counter] == '--j':
			counter=counter+2
			continue
		if l[counter] == '--i':
			if l[counter+1].split('/')[0] == 'Select':
				selectflag=l[counter+1]
		newcmd.append(l[counter])
 		counter=counter+1
	return ' '.join(newcmd),selectflag

#==============================
def parseCMDrefine_movie(relioncmd):

        l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
        selectflag=''
        while counter < tot:
                if l[counter] == '--preread_images':
                        counter=counter+1
                        continue
                if l[counter] == '--pool':
                        counter=counter+2
                        continue
                if l[counter] == '`which':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_refine_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_refine`':
                        counter=counter+1
                        continue
		if l[counter] == '--j':
                        counter=counter+2
                        continue
                if l[counter] == '--gpu':
                        if counter+1 < tot:
                                if l[counter+1][0] == '-':
                                        counter=counter+1
                                else:
                                        counter=counter+2
                        else:
                                counter=counter+1
                        continue
                if l[counter] == '--j':
                        counter=counter+2
                        continue
                if l[counter] == '--i':
                        if l[counter+1].split('/')[0] == 'Select':
                                selectflag=l[counter+1]
                newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd),selectflag

#==============================
def getSelectParticleDir(selectdir):

	r1=open(selectdir,'r')
	imagenumcol=3
	for line in r1:
		if len(line) < 40:
			if len(line.split()) > 0:
				if line.split()[0] == '_rlnImageName':
					imagenumcol=int(line.split()[1].split('#')[-1])-1
	r1.close()
	r1=open(selectdir,'r')
	skip=0
	for line in r1:
		if len(line) < 40:
			continue
		if len(line.split()) > 3:
			if skip == 0:
				micname=line.split()[imagenumcol]
				skype=1
	r1.close()
	jobname=micname.split('@')[-1].split('/')[1]

	return 'Extract/%s' %(jobname)

#=============================
def parseCMDautopick(relioncmd):

	l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
	while counter < tot:
		if l[counter] == '`which':
                        counter=counter+1
                        continue
		if l[counter] == 'relion_autopick_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_autopick`':
                        counter=counter+1
			continue
		if l[counter] == '--gpu':
                        counter=counter+2
                        continue
		newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd)

#=============================
def parseCMDctf(relioncmd):

	l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
        downloadbinned=False
        while counter < tot:
                if l[counter] == '`which':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_run_ctffind_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_run_ctffind`':
                        counter=counter+1
                        continue
                if l[counter] == '--gpu':
                        counter=counter+1
                        continue
		if len(l[counter].split('_exe')) > 1:
                        counter=counter+1
                        continue
                newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd),downloadbinned

#=============================
def parseCMDmovie(relioncmd):

	l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
        downloadbinned=False
	while counter < tot:
                if l[counter] == '`which':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_run_motioncorr_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_run_motioncorr`':
                        counter=counter+1
                        continue
		if l[counter] == '--gpu':
			counter=counter+2
			continue
		if l[counter] == '--i':
			counter=counter+2
        		continue
		if l[counter] == '--binnedMicsOnly':
			downloadbinned=True
			counter=counter+1
			continue
		if len(l[counter].split('_exe')) > 1:
			counter=counter+1
	        	continue
		newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd),downloadbinned

#==============================
def parseCMDpreprocess_movie(relioncmd):

        l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
        while counter < tot:
                if l[counter] == '`which':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_preprocess_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_preprocess`':
                        counter=counter+1
                        continue
		if l[counter] == '--i':
                        counter=counter+2
                        continue
                newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd)

#==============================
def parseCMDpreprocess(relioncmd):

        l=relioncmd.split()
        newcmd=[]
        tot=len(l)
        counter=0
        while counter < tot:
                if l[counter] == '`which':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_preprocess_mpi`':
                        counter=counter+1
                        continue
                if l[counter] == 'relion_preprocess`':
                        counter=counter+1
                        continue
                newcmd.append(l[counter])
                counter=counter+1
        return ' '.join(newcmd)

#==============================
def relion_refine_mpi(project):

	#Set entry
	otherPartDir=''
	otherPartRclone=''
	error=''

	#Get relion command and input options
	relioncmd,particledir,initmodel,outdir,autoref,numiters,partstarname,mask,stack,continueRun,outbasename,diameter=getCMDrefine(infile)

	if os.path.exists('%s/run.err' %(outdir)): 
		os.remove('%s/run.err' %(outdir))
		cmd='touch %s/run.err' %(outdir)
		subprocess.Popen(cmd,shell=True).wait()

	if len(continueRun) > 0: 
		particledir=continueRun.split('/')
		del particledir[-1]
		particledir='/'.join(particledir)
		partstarname='%s_data.star' %(continueRun.split('/')[-1][:-15])
		for line in open(continueRun,'r'): 
			if len(line) > 4: 
				if line.split()[0] == '_rlnCurrentIteration': 
					iterationNumOpt=int(line.split()[1].strip())
		if float(iterationNumOpt) >= float(numiters): 
			writeToLog('Error: Number of iterations requested %i is less than / equal to current iteration of data (%i). Exiting' %(numiters,iterationNumOpt),'%s/run.err' %(outdir))
			sys.exit()

	if len(particledir) == 0: 
		particledir=partstarname	

	#Get number of particles to decide how big of a machine to spin up
	if stack is False:
		if len(particledir) == 0: 
			starfilename=particledir
			numParticles=len(open(particledir,'r').readlines())
		if len(particledir) > 0: 
			starfilename='%s/%s' %(particledir,partstarname)
			numParticles=len(open('%s/%s' %(particledir,partstarname),'r').readlines())
		magcheck=False
		pixcheck=False
		ctfcheck=False
		partcolnum=-1
		detectorcolnum=-1
		magcolnum=-1
		exampleline=''	
		for line in open(starfilename,'r'):
			if len(line.split()) > 0: 
				if line.split()[0] == '_rlnMagnification': 
					magcheck=True
					magcolnum=int(line.split()[1].split('#')[-1])
				if line.split()[0] == '_rlnDetectorPixelSize': 
					pixcheck=True
					detectorcolnum=int(line.split()[1].split('#')[-1])
				if line.split()[0] == '_rlnDefocusU': 
					ctfcheck=True
				if line.split()[0] == '_rlnImageName': 
					partcolnum=int(line.split()[1].split('#')[-1])
				exampleline=line
		ctfin=False
		apixin=False
		rlncounter=1
		while rlncounter <= len(relioncmd.split()): 
			if relioncmd.split()[rlncounter-1] == '--ctf': 
				ctfin=True
			if relioncmd.split()[rlncounter-1] == '--angpix': 
				apixin=True
				apixVal=float(relioncmd.split()[rlncounter])
			rlncounter=rlncounter+1
		if partcolnum < 0: 
			writeToLog('Error: could not find _rlnImageName in .star file. Exiting','%s/run.err' %(outdir))
			sys.exit()
		if apixin is False: 
			if magcheck is False: 
				writeToLog('Error: No magnification information found in .star file. Exiting', '%s/run.err' %(outdir))
				sys.exit()
		if apixin is False: 
                        if pixcheck is False:
                                writeToLog('Error: No detector pixel size information found in .star file. Exiting', '%s/run.err' %(outdir))
                                sys.exit()
		if ctfin is True: 
			if ctfcheck is False: 
				writeToLog('Error: no defocus information found in .star file. Exiting', '%s/run.err' %(outdir))
				sys.exit()

		#Get xdims
		if len(exampleline) == 0: 			
			writeToLog('Error: no inputline found','%s/run.err' %(outdir))
			sys.exit()
		examplePart=exampleline.split()[partcolnum-1]
		if os.path.exists('%s/handler.txt' %(outdir)):
                        os.remove('%s/handler.txt' %(outdir))
                cmd='relion_image_handler --i %s --stats > %s/handler.txt' %(examplePart,outdir)
		subprocess.Popen(cmd,shell=True).wait()
		partxdim=int(linecache.getline('%s/handler.txt' %(outdir),1).split('=')[1].split('x')[0].strip())	

		if apixin is False:
			if len(exampleline.split()) < detectorcolnum-1: 
				writeToLog('Error: particle line is missing columns: %s' %(exampleline), '%s/run.err' %(outdir))
				sys.exit()
			example_detector=float(exampleline.split()[detectorcolnum-1])
			example_mag=float(exampleline.split()[magcolnum-1])
			apixVal=(example_detector/example_mag)*10000
	if stack is True:
		if partstarname.split('.')[-1] != 'mrcs': 
			writeToLog('Error: input stack must have .mrcs extension. Exiting','%s/run.err' %(outdir))
			sys.exit()
		if os.path.exists('%s/handler.txt' %(outdir)): 
			os.remove('%s/handler.txt' %(outdir)) 
		cmd='relion_image_handler --i %s --stats > %s/handler.txt' %(partstarname,outdir)
                subprocess.Popen(cmd,shell=True).wait()
                numParticles=int(linecache.getline('%s/handler.txt' %(outdir),1).split('=')[1].split('x')[3].split(';')[0])
		partxdim=int(linecache.getline('%s/handler.txt' %(outdir),1).split('=')[1].split('x')[0].strip())
		ctf=False
		angpix=False
		rlncounter=1
                while rlncounter <= len(relioncmd.split()):
                        if relioncmd.split()[rlncounter-1] == '--ctf':
                                ctf=True
                        if relioncmd.split()[rlncounter-1] == '--angpix':
                                angpix=True
                                apixVal=float(relioncmd.split()[rlncounter])
                        rlncounter=rlncounter+1
		if ctf is True: 
			writeToLog('Error: CTF correction was selected for a particle stack without a star file (which means that Relion cannot do CTF correction). Exiting','%s/run.err' %(outdir))
			sys.exit()
		if angpix is False: 
			writeToLog('Error: Pixel size required. Please include --angpix into "Additional arguments" and resubmit','%s/run.err' %(outdir))
			sys.exit()
	if initmodel != 'None': 
		if os.path.exists('handler2.txt'): 
			os.remove('handler2.txt')
		time.sleep(2)
		cmd='relion_image_handler --i %s --stats > handler2.txt' %(initmodel)
		subprocess.Popen(cmd,shell=True).wait()	
		time.sleep(2)
		modxdim=int(linecache.getline('handler2.txt',1).split('=')[1].split('x')[0].strip())
		os.remove('handler2.txt')
		if modxdim != partxdim: 
			writeToLog('Error: 3D model and particles do not have the same dimensions. Exiting','%s/run.err' %(outdir))
			sys.exit()

	#Check that diameter specified fits within box
	if float(diameter) >= float(apixVal)*float(partxdim)-1: 
		writeToLog('Error: Diameter specified (%.0f Angstroms) is greater than box size (%.0f Angstroms). Exiting' %(diameter,apixVal*partxdim),'%s/run.err' %(outdir))
		writeToLog('Error: Diameter specified (%.0f Angstroms) is greater than box size (%.0f Angstroms). Exiting' %(diameter,apixVal*partxdim),'%s/run.out' %(outdir))
		sys.exit() 

	#Re-write note.txt without 'Kill'
	cmd='mv %s/note.txt %s/note_bckup.txt' %(outdir,outdir)
	subprocess.Popen(cmd,shell=True).wait()
	newNoteOut=open('%s/note.txt' %(outdir),'w')
	for line in open('%s/note_bckup.txt' %(outdir),'r'): 
		if 'Kill' not in line: 
			newNoteOut.write(line)
	newNoteOut.close()
	os.remove('%s/note_bckup.txt' %(outdir))

	#Parse relion command to only include input options, removing any mention of 'gpu' or j threads in command
	relioncmd,select=parseCMDrefine(relioncmd)
	#Check where input particles are located
	if stack is False: 
		otherPartDir,otherPartRclone,error=checkPartLocation(starfilename,particledir)
	if len(error) > 0: 
		writeToLog(error,'%s/run.err' %(outdir))
                sys.exit()
	if len(otherPartRclone) > 0: 
		if os.path.exists('rclonetmplist1298.txt'): 
			os.remove('rclonetmplist1298.txt')
		o89=open('rclonetmplist1298.txt','w')
		for entry in otherPartRclone: 
			o89.write('%s\n' %(entry.strip()))
		o89.close()
		otherPartRclone='rclonetmplist1298.txt'
	#Choose instance type
	if initmodel == 'None': #2D classification
		if numParticles < 20000:
			instance='p2.xlarge'
		if numParticles >= 20000 and numParticles <= 100000:
                        instance='p2.8xlarge'
		if numParticles > 100000:
                        instance='p2.16xlarge'
	if initmodel != 'None': #3D classification or refinement
		if autoref == -1: #3D classification
			if numParticles <25000:
				instance='p2.xlarge'
			if numParticles >=25000:
				instance='p2.8xlarge'
		if autoref != -1: #3D refinement
			instance='p2.8xlarge'
	#Get AWS region from aws_init.sh environment variable
	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	writeToLog('Booting up virtual machine %s on AWS in availability zone %sa' %(instance,awsregion), '%s/run.out' %(outdir))

	#Get AWS ID
	AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

	#Get AWS CLI directory location
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
		print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
		sys.exit()

	#.aws_relion will Have: [particledir] [s3 bucket name] [ebs volume]
	ebs_exist=False
	s3_exist=False
	bucketname=''
	if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
                        if line.split()[0] == particledir:
				bucketname=line.split()[1]
				ebsvolname=line.split()[2]
				#Check if it exists:
				if os.path.exists('%s/ebsout.log' %(outdir)):
					os.remove('%s/ebsout.log' %(outdir))
				cmd='aws ec2 describe-volumes | grep VolumeId > %s/ebsout.log' %(outdir)
 				subprocess.Popen(cmd,shell=True).wait()
				for line in open('%s/ebsout.log' %(outdir),'r'):
					if line.strip().split()[-1].split('"')[1] == ebsvolname:
						ebs_exist=True
						volID=ebsvolname
				os.remove('%s/ebsout.log' %(outdir))
				if os.path.exists('%s/s3out.log' %(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
                                subprocess.Popen(cmd,shell=True).wait()
                                if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0:
                                        s3_exist=True
	keyname=keypair.split('/')[-1].split('.pem')[0]
        keyname=keyname.split('_')
        keyname='-'.join(keyname)
        outdirname=outdir.split('/')
        if len(outdirname[-1]) == 0:
                del outdirname[-1]
        outdirname='-'.join(outdirname)
        outdirname=outdirname.lower().strip()
        keyname=keyname.lower().strip()
        project=project.strip()
	if s3_exist is False:
		if ebs_exist is True:
			ebs_exist=False
			cmd='aws ec2 delete-volume --volume-id %s' %(ebsvolname)
			subprocess.Popen(cmd,shell=True).wait()
	if len(otherPartDir) == 0: 
		inputfilesize=subprocess.Popen('du %s' %(particledir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-2]
	if len(otherPartDir) > 0: 
		inputfilesize=subprocess.Popen('du %s' %(otherPartDir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-2]
	sizeneeded='%.0f' %(math.ceil((float(inputfilesize)*4)/1000000))
        actualsize='%.0f' %(math.ceil((float(inputfilesize)/1000000)))
	#Upload data to S3
	if s3_exist is False:
		writeToLog('Started uploading %sGB to AWS on %s' %(actualsize,time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
		if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time()) 
		if len(project) > 0: 
			bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                	numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
	                numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if len(otherPartRclone) == 0: 
			bucketname=rclone_to_s3(particledir,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project,otherPartRclone)
		if len(otherPartRclone) > 0: 
			bucketname=rclone_to_s3(otherPartDir,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project,otherPartRclone)
		writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
	if ebs_exist is False:
		writeToLog('Creating data storage drive ...','%s/run.out' %(outdir))
        	#Create EBS volume
        	if os.path.exists('%s/awsebs.log' %(outdir)) :
                	os.remove('%s/awsebs.log' %(outdir))
        	cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%s"'%(awsdir,int(sizeneeded),awsregion,teamname,particledir)+'> %s/awsebs.log' %(outdir)
        	subprocess.Popen(cmd,shell=True).wait()

        	#Get volID from logfile
        	volID=linecache.getline('%s/awsebs.log' %(outdir),5).split('ID: ')[-1].split()[0]

	#Restore volume, returning with it volID for later steps
	writeToLog('Launching virtual machine %s...' %(instance),'%s/run.out' %(outdir))
	now=datetime.datetime.now()
	startday=now.day
	starthr=now.hour
	startmin=now.minute

	#Launch instance
	if os.path.exists('%s/awslog.log' %(outdir)):
		os.remove('%s/awslog.log' %(outdir))
	cmd='%s/launch_AWS_instance.py --instance=%s --availZone=%sa --volume=%s > %s/awslog.log' %(awsdir,instance,awsregion,volID,outdir)
	subprocess.Popen(cmd,shell=True).wait()
	#Get instance ID, keypair, and username:IP
	instanceID=subprocess.Popen('cat %s/awslog.log | grep ID' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
	keypair=subprocess.Popen('cat %s/awslog.log | grep ssh' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
	userIP=subprocess.Popen('cat %s/awslog.log | grep ssh' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()

	#Create directories on AWS
	if instance == 'p2.xlarge':
                gpu='--gpu '
                j='--j 2 '
                mpi=2
                numfiles=8
		cost=0.9
        if instance == 'p2.8xlarge':
                gpu='--gpu '
                j='--j 3 '
                mpi=9
                numfiles=50
		cost=7.20
        if instance == 'p2.16xlarge':
                gpu='--gpu '
                j='--j 3 '
                mpi=17
                numfiles=90
		cost=14.40
	env.host_string='ubuntu@%s' %(userIP)
        env.key_filename = '%s' %(keypair)
	if ebs_exist is False:
		writeToLog('Started transferring %sGB at %s' %(actualsize,time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
		dirlocation='/data'
		if stack is False: 
			for entry in particledir.split('/'):
				if len(entry.split('.star')) == 1:
					exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
					dirlocation=dirlocation+'/'+entry
		if len(otherPartDir) == 0: 
			if stack is False: 
				s3_to_ebs(userIP,keypair,bucketname,'/data/%s/' %(particledir),'%s/rclone' %(awsdir),key_ID,secret_ID,awsregion,numfiles)
			if stack is True: 
				s3_to_ebs(userIP,keypair,bucketname,'/data/%s' %(particledir),'%s/rclone' %(awsdir),key_ID,secret_ID,awsregion,numfiles)
		if len(otherPartDir) > 0: 
			s3_to_ebs(userIP,keypair,bucketname,'/data/%s/' %(otherPartDir),'%s/rclone' %(awsdir),key_ID,secret_ID,awsregion,numfiles)
		writeToLog('Finished transfer at %s' %(time.asctime( time.localtime(time.time()) )),'%s/run.out' %(outdir))

	#Make output directories
	dirlocation='/data'
	outdirlist=outdir.split('/')
	del outdirlist[-1]
        for entry in outdirlist:
        	exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                dirlocation=dirlocation+'/'+entry
	cmd='rsync -avzu --rsync-path="rsync" --log-file="%s/rsync.log" -e "ssh -q -o StrictHostKeyChecking=no -i %s" %s ubuntu@%s:%s/ > %s/rsync.log' %(outdir,keypair,outdir,userIP,dirlocation,outdir)
    	subprocess.Popen(cmd,shell=True).wait()
	if len(otherPartDir) > 0: 
		dirlocation='/data/'
		partdirlist=particledir.split('/')
		del partdirlist[-1]
		for entry in partdirlist:
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
			dirlocation=dirlocation+'/'+entry
		cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -e "ssh -q -o StrictHostKeyChecking=no -i %s" %s ubuntu@%s:%s/ > %s/rsync.log' %(outdir,keypair,particledir,userIP,dirlocation,outdir)
		subprocess.Popen(cmd,shell=True).wait()
	if initmodel != 'None':
		cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -R -e "ssh -q -o StrictHostKeyChecking=no -i %s" %s ubuntu@%s:/data/ > %s/rsync.log' %(outdir,keypair,initmodel,userIP,outdir)
        	subprocess.Popen(cmd,shell=True).wait()
	if len(mask) > 0:
                cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -R -e "ssh -q -o StrictHostKeyChecking=no -i %s" %s ubuntu@%s:/data/ > %s/rsync.log' %(outdir,keypair,mask,userIP,outdir)
                subprocess.Popen(cmd,shell=True).wait()

	relion_remote_cmd='mpirun -np %i /home/EM_Packages/relion2.0/build/bin/relion_refine_mpi %s %s %s' %(mpi,relioncmd,j,gpu)

	o2=open('run_aws.job','w')
	o2.write('#!/bin/bash\n')
	o2.write('cd /data\n')
	o2.write('%s\n' %(relion_remote_cmd))
	o2.close()
	st = os.stat('run_aws.job')
	os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
	cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > %s/rsync.log' %(outdir,keypair,userIP,outdir)
	subprocess.Popen(cmd,shell=True).wait()
	cmd='ssh -q -n -f -i %s ubuntu@%s "export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:$LD_LIBRARY_PATH && nohup ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,userIP,outdir,outdir)
	subprocess.Popen(cmd,shell=True)

	writeToLog('Job submitted to the cloud...','%s/run.out' %(outdir))
	cmd='scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i %s %s/run.out ubuntu@%s:/data/%s/ > %s/rsync.log' %(keypair,outdir,userIP,outdir,outdir)
	subprocess.Popen(cmd,shell=True)
	isdone=0
	
	while isdone == 0:
		cmd='rsync --rsync-path="rsync" --log-file="%s/rsync.log" -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(outdir,keypair,userIP,outdir,outdir,outdir)
		subprocess.Popen(cmd,shell=True).wait()
		time.sleep(2)
		if autoref == -1:
			if os.path.exists('%s_it%03i_data.star' %(outbasename,int(numiters))):	
				isdone=1
		if autoref != -1: 
			if os.path.exists('%s_class001.mrc' %(outbasename)): 
				isdone=1
		#Check if job was specified to be killed
		if isdone ==0:
 			isdone=check_and_kill_job('%s/note.txt' %(outdir),userIP,keypair)

		#Check if there are any errors
		if isdone == 0: 
			if os.path.exists('%s/run.err' %(outdir)): 
				if float(subprocess.Popen('cat %s/run.err | wc -l' %(outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()) > 0: 
					writeToLog('\nError detected in run.err. Shutting down instance.','%s/run.out' %(outdir))
					isdone=1

		time.sleep(10)
	time.sleep(30)

	writeToLog('Job finished!','%s/run.out' %(outdir))
	writeToLog('Shutting everything down ...','%s/run.out' %(outdir))
	cmd=subprocess.Popen('aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	isdone=0
	#while isdone == 0:
	#	status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
	#	if status == 'terminated':
	#		isdone=1
	#	time.sleep(10)
	
	now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
        	deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
		cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
		subprocess.Popen(cmd,shell=True).wait()
		cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
	cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(particledir,outdir,float(deltaHr)*float(cost))
        subprocess.Popen(cmd,shell=True).wait()

	#Update .aws_relion
	if os.path.exists('.aws_relion_tmp'):
		os.remove('.aws_relion_tmp')
	if os.path.exists('.aws_relion'):
		shutil.move('.aws_relion','.aws_relion_tmp')
		tmpout=open('.aws_relion','w')
		for line in open('.aws_relion_tmp','r'):
			if line.split()[0] == particledir:
				continue
			tmpout.write(line)
		tmpout.close()
	        os.remove('.aws_relion_tmp')

	cmd='echo "%s     %s      %s" >> .aws_relion' %(particledir,bucketname,volID)
	subprocess.Popen(cmd,shell=True).wait()

	if len(project) > 0:
                projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)
                cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                if os.path.exists('.aws_relion_project_info'):
                        cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 sync %s/ s3://%s/%s > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                guilist=glob.glob('.gui*')
                for gui in guilist:
                        cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()
                if os.path.exists('%s/s3tmp.log' %(outdir)):
                        os.remove('%s/s3tmp.log' %(outdir))
	
	#Cleanup
	if os.path.exists('%s/awslog.log' %(outdir)):
		os.remove('%s/awslog.log' %(outdir))
	if os.path.exists('%s/awsebs.log' %(outdir)):
		os.remove('%s/awsebs.log' %(outdir))
	if os.path.exists('run_aws.job'): 
		os.remove('run_aws.job')
	if os.path.exists('rclonetmplist1298.txt'): 
		os.remove('rclonetmplist1298.txt')
	if os.path.exists('rclone.conf'): 
		os.remove('rclone.conf')
	if os.path.exists('runningProcs.txt'): 
		os.remove('runningProcs.txt')

#==============================
def check_and_kill_job(note,IP,keypair):

	o9=open(note,'r')
	kill=0
	for line in o9:
		if len(line.split()) > 0:
			if line.split()[0] == 'Kill':
				kill=1
			if line.split()[0] == 'kill':
        	                kill=1
	if kill == 1:
		kill_job(keypair,IP)
	o9.close()

	return kill

#====================
def kill_job(keypair,IP):

	env.host_string='ubuntu@%s' %(IP)
        env.key_filename = '%s' %(keypair)
	exec_remote_cmd('ps aux | grep mpi > runningProcs.txt')

	cmd='scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i %s ubuntu@%s:~/runningProcs.txt .' %(keypair,IP)
	subprocess.Popen(cmd,shell=True).wait()

	pidlist=[]

	for proc in open('runningProcs.txt','r'):
		if 'refine_mpi' in proc:
			pidlist.append(proc.split()[1])

	for pid in pidlist:
		exec_remote_cmd('kill -9 %s' %(pid))

#==============================
def getCMDctf(infile):

	o1=open(infile,'r')
        for line in o1:
                if len(line.split('=')) > 0:
                        if line.split('=')[0] == 'relioncmd':
                                rlncmd=line.split('=')[1]
	o1.close()
        counter=1
	ifGctf=False
	#Get particle input directory and if there is a reference model
        for l in rlncmd.split():
                if l == '--i':
                        micstar=counter
		if l == '--o':
                        outdir=counter
		if l == '--use_gctf':
			ifGctf = True
		counter=counter+1
	micstar=rlncmd.split()[micstar]
        outdir=rlncmd.split()[outdir]
	return rlncmd,micstar,outdir,ifGctf

#==============================
def getCMDautopick(infile):

        o1=open(infile,'r')
	flag=0
        for line in o1:
		if flag == 0:
	                if len(line.split('=')) > 0:
        	                if line.split('=')[0] == 'relioncmd':
                	                rlncmd=line.split('=')[1]
					flag=1
	o1.close()
        counter=1
	killProcess=''
   	ref=''
        #Get particle input directory and if there is a reference model
        for l in rlncmd.split():
                if l == '--i':
                        micstar=counter
                if l == '--odir':
                        outdir=counter
                if l == '--ref':
                        ref=counter
		if l == '--read_fom_maps':
			killProcess='--read_fom_maps'
		if l == '--write_fom_maps':
			killProcess='--write_fom_maps'
                counter=counter+1
        micstar=rlncmd.split()[micstar]
        outdir=rlncmd.split()[outdir]
	if ref != '':
		ref=rlncmd.split()[ref]
        return rlncmd,micstar,outdir,ref,killProcess

#==============================
def checkDoseInputs(infile): 
	o1=open(infile,'r')
        for line in o1:
                if len(line.split('=')) > 0:
                        if line.split('=')[0] == 'relioncmd':
                                rlncmd=line.split('=')[1]
	o1.close()
	errormsg=''
	checkdose=False
	for l in rlncmd.split(): 
		if l == '--dose_weighting':
			checkdose=True
	patchxnum=0
	patchynum=0
	kevnum=0
	dosenum=0
	prenum=0
	counter=1
	if checkdose is True:
		for l in rlncmd.split():
			if l=='--patch_x': 
				patchxnum=counter+1
			if l=='--patch_y':
        	                patchynum=counter+1		
			if l=='--voltage': 
				kevnum=counter+1
			if l=='--dose_per_frame':
				dosenum=counter+1
			if l=='--preexposure':
				prenum=counter+1
		if patchxnum==0: 
			errormsg=errormsg+' Could not find value for Patch X, '
		if patchynum==0:
			errormsg=errormsg+' Could not find value for Patch Y, '
		if kevnum ==0:
			errormsg=errormsg+' Could not find value for accelerating voltage (kev) '
		if dosenum == 0: 
			errormsg=errormsg+' Could not find dose per frame information '
		if prenum == 0: 
			errormsg=errormsg+' Could not find pre-exposure information '
			
	return errormsg,checkdose
#==============================
def getCMDmovie(infile):
	o1=open(infile,'r')
        for line in o1:
                if len(line.split('=')) > 0:
                        if line.split('=')[0] == 'relioncmd':
                                rlncmd=line.split('=')[1]
	o1.close()
        counter=1
	ifMotionCor2=False
        savemovies=False
	gainref=-1
	angpix=-1
	#Get particle input directory and if there is a reference model
        for l in rlncmd.split():
                if l == '--i':
                        micstar=counter
                if l == '--motioncorr_exe':
                        aligntype='motioncorr'
		if l == '--use_motioncor2':
			ifMotionCor2=True
		if l == '--angpix':
			angpix=counter
		if l == '--unblur_exe':
			aligntype='unblur'
                if l == '--gainref':
			gainref=counter
		if l == '--o':
                        outdir=counter
		if l == '--save_movies':
			savemovies=True
                counter=counter+1

	micstar=rlncmd.split()[micstar]
        outdir=rlncmd.split()[outdir]
	if gainref > 0:
		gainref=rlncmd.split()[gainref]
	if angpix > 0:
		angpix=float(rlncmd.split()[angpix])
        return rlncmd,micstar,outdir,gainref,aligntype,ifMotionCor2,savemovies,angpix

#==============================
def getCMDpreprocess(infile):
	o1=open(infile,'r')
        for line in o1:
		if len(line.split('=')) > 0:
			if line.split('=')[0] == 'relioncmd':
                                rlncmd=line.split('=')[1]
        o1.close()
	counter=1
        #Get particle input directory and if there is a reference model
        for l in rlncmd.split():
                if l == '--i':
                        micstar=counter
                if l == '--coord_dir':
                        boxdir=counter
                if l == '--part_dir':
                        outdir=counter
                counter=counter+1

        micstar=rlncmd.split()[micstar]
        outdir=rlncmd.split()[outdir].split('run')[0]
        boxdir=rlncmd.split()[boxdir].strip()

	return rlncmd,micstar,boxdir,outdir

#==============================
def getCMDpreprocessMovie(infile):
        o1=open(infile,'r')
        for line in o1:
                if len(line.split('=')) > 0:
                        if line.split('=')[0] == 'relioncmd':
                                rlncmd=line.split('=')[1]
        			if 'preprocess' in rlncmd: 
					counter=1
					#Get particle input directory and if there is a reference model
				        #relioncmd=`which relion_preprocess_mpi` --i MotionCorr/job002/corrected_micrograph_movies.star --reextract_data_star Refine3D/job019/run_it014_data.star --part_dir MovieRefine/job100/ --list_star MovieRefine/job100/micrographs_movie_list.star --join_nr_mics -1 --part_star MovieRefine/job100/particles_movie.star --extract --extract_movies --extract_size 100 --movie_name movie --first_movie_frame 1 --last_movie_frame 16 --avg_movie_frames 1 --norm --bg_radius 30 --white_dust -1 --black_dust -1 --invert_contrast
					for l in rlncmd.split():
				                if l == '--i':
				                        micstar=counter
			                	if l == '--part_dir':
                        				outdir=counter
				                if l == '--reextract_data_star':
							rext=counter
						if l == '--movie_name': 
							movenamenum=counter
						counter=counter+1
				        micstar=rlncmd.split()[micstar]
				        outdir=rlncmd.split()[outdir].split('run')[0]
					boxdir=rlncmd.split()[rext]
					moviename=rlncmd.split()[movenamenum]
					#Get first line to check where extracted particles are located
					#Get header col val first
					e1=open(boxdir,'r')
					for eline in e1:
						if len(eline)>0: 
							if len(eline.split())>1:
								if eline.split()[0] == '_rlnImageName': 
									Ecolnum=int(eline.split()[1].split('#')[-1])
								if eline.split()[0] == '_rlnMicrographName':
									Emicnum=int(eline.split()[1].split('#')[-1])
					e1.close()
					flag=0
					e1=open(boxdir,'r')
                                        for eline in e1:
                                                if len(eline)>0:
                                                        if len(eline.split())>8:
								if flag == 0:
									eStack=eline.split()[Ecolnum-1].split('@')[-1].replace('//','/')
									eMic=eline.split()[Emicnum-1].replace('//','/')
									if len(eStack.split('/')) == 4: 
										extractDir=eStack.split('/')[0]+'/'+eStack.split('/')[1]	
					boxbase=boxdir.split('data.star')[0]
					boxdir=boxdir.split('/')
					del boxdir[-1]
					boxdir='/'.join(boxdir)	
					rlncmdpre=rlncmd
				if 'refine' in rlncmd: 
					#Get particle input directory and if there is a reference model
				        outbasenanme=''
				        continuecounter=-1
				        indircounter=-1
				        refcounter=-1
				        outcounter=-1
				        autoref=-1
				        counter=1
				        itercounter=0
				        numiters=0
				        mask=''
				        maskcounter=-1
				        ref='None'
				        stack=False
				        partstarname=''
				        partdir=''
				        contLocation=''
				        particlediameter=-999
				        partdiamcounter=-1
				        for l in rlncmd.split():
				                if l == '--i':
				                        indircounter=counter
				                if l == '--ref':
				                        refcounter=counter
				                if l == '--o':
				                        outcounter=counter
				                if l == '--auto_refine':
				                        autoref=counter
				                if l == '--iter':
				                        itercounter=counter
					        if l == '--solvent_mask':
				                        maskcounter=counter
				                if l == '--continue':
				                        continuecounter=counter
					        if l == '--particle_diameter':
				                        partdiamcounter=counter
				                counter=counter+1

				        if indircounter > 0:
				                partstarname=rlncmd.split()[indircounter].split('/')[-1]
				                if '.star' not in partstarname:
				                        stack=True
				                partdir=rlncmd.split()[indircounter].split('/')
				                del partdir[-1]
				                partdir='/'.join(partdir)
				        if partdiamcounter > 0:
				                particlediameter=float(rlncmd.split()[partdiamcounter])
				        outbasename=rlncmd.split()[outcounter]
				        outdir=rlncmd.split()[outcounter].split('/')
				        del outdir[-1]
				        outdir='/'.join(outdir)
				        if itercounter > 0:
				                numiters=int(rlncmd.split()[itercounter])
				        if refcounter > 0:
				                ref=rlncmd.split()[refcounter]
				        if maskcounter > 0:
				                mask=rlncmd.split()[maskcounter]
				        if continuecounter > 0:
				                contLocation=rlncmd.split()[continuecounter]
					rlncmdrefine=rlncmd
				#return rlncmd,partdir,ref,outdir,autoref,numiters,partstarname,mask,stack,contLocation,outbasename,particlediameter
					
        return rlncmdpre,micstar,boxdir,boxbase,moviename,outdir,extractDir,rlncmdrefine,partdir,ref,outdir,outbasename,autoref,numiters,partstarname,mask,stack,contLocation,outbasename,particlediameter

#==============================
def getMicStarFileSize(micstar):
	miccounter=0
	for line in open(micstar,'r'):
		if len(line) < 40:
			if line.split()[0] == '_rlnMicrographName':
				miccol=int(line.split()[1].split('#')[-1])
			continue
		if miccounter==1:
			mic=line.split()[miccol-1]
		miccounter=miccounter+1
	return float(os.stat(mic).st_size)*miccounter

#==============================
def relion_movie_refine(project):

	#Get relion command and input options
	rlncmdpre,micstar,boxdir,boxbase,moviename,outdir,extractDir,rlncmdrefine,partdir,ref,outdirRef,outdirRefFull,autoref,numiters,partstarname,mask,stack,contLocation,outbasename,particlediameter=getCMDpreprocessMovie(infile)

	#Parse relion command to only include input options, removing any mention of 'gpu' or j threads in command
	relioncmdpre=parseCMDpreprocess_movie(rlncmdpre)
	relioncmdrefine=parseCMDrefine_movie(rlncmdrefine)
	
	#Get number of particles
	numParticlesIn=float(subprocess.Popen('cat %s_data.star | grep mrc | wc -l' %(contLocation[:-15]), shell=True, stdout=subprocess.PIPE).stdout.read().strip())

	#Choose instance type
	instance='d2.8xlarge'
        numInstancesRequired=8
	mpi=36
	drives='/dev/xvdb /dev/xvdc /dev/xvdd /dev/xvde /dev/xvdf /dev/xvdg /dev/xvdh /dev/xvdi /dev/xvdj /dev/xvdk /dev/xvdl /dev/xvdm /dev/xvdn /dev/xvdo /dev/xvdp /dev/xvdq /dev/xvdr /dev/xvds /dev/xvdt /dev/xvdu /dev/xvdv /dev/xvdw /dev/xvdx /dev/xvdy'
	#drives='/dev/xvdb /dev/xvdc /dev/xvdd'
	numRaid=24
	cost=5.52
			
	#Refinement instance
	Refinstance='x1.32xlarge'
	Refmpi=128
	Refcost=13.338
	Refdrives='/dev/xvdb /dev/xvdc'
	RefnumRaid=2
	#Refdrives=drives
	#RefnumRaid=numRaid

	#Get AWS region from aws_init.sh environment variable
	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	writeToLog('Booting up %i x %s virtual machines on AWS in availability zone %sa' %(numInstancesRequired,instance,awsregion), '%s/run.out' %(outdir))

	#Get AWS CLI directory location
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
		print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
		sys.exit()

	#Get AWS ID
	AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

	#Get AWS CLI directory location
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
		print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
		sys.exit()

	#.aws_relion will Have: [particledir] [s3 bucket name] [ebs volume]
	ebs_exist=False
	s3_exist=False
	bucketname=''
	if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
                        if line.split()[0].strip() == micstar.strip():
                                bucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log'%(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
				subprocess.Popen(cmd,shell=True).wait()
                                if len(open('%s/s3out.log'%(outdir),'r').readlines()) > 0:
                                        s3_exist=True
	#Check extract directory extractDir
	Eebs_exist=False
        Es3_exist=False
        Ebucketname=''
        if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
                        if line.split()[0].strip() == boxdir.strip():
                                Ebucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log'%(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(Ebucketname.split('s3://')[-1],outdir)
                                subprocess.Popen(cmd,shell=True).wait()
                                if len(open('%s/s3out.log'%(outdir),'r').readlines()) > 0:
                                        Es3_exist=True

	keyname=keypair.split('/')[-1].split('.pem')[0]
        keyname=keyname.split('_')
        keyname='-'.join(keyname)
        outdirname=outdir.split('/')
        if len(outdirname[-1]) == 0:
                del outdirname[-1]
        outdirname='-'.join(outdirname)
        outdirname=outdirname.lower().strip()
        keyname=keyname.lower().strip()
        project=project.strip()
	indirname=micstar.split('/')
	del indirname[-1]
	indirname='-'.join(indirname)
	indirname=indirname.lower().strip()

	#Upload data to S3
	if s3_exist is False and len(micstar.split('s3-')) == 1:
		writeToLog('Started upload of movies to AWS on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
		if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
                if len(project) > 0:
                        bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,indirname)
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                	numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
	                numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		bucketname,micdir,origdir=rclone_to_s3_preprocess(micstar,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project)
		writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
		inputfilesize=subprocess.Popen('du %s' %(micdir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-2]
		sizeneeded='%.0f' %(math.ceil((float(inputfilesize)*8)/1000000))
	        actualsize='%.0f' %(math.ceil((float(inputfilesize)/1000000)))

	if len(micstar.split('s3-')) > 1:
                micstarinput=micstar.split('s3-')[-1]
                if micstarinput[-1] == '/':
                        micstarinput=micstarinput[:-1]
                if len(project) == 0:
                        bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
                if len(project) > 0:
                        bucketname='rln-aws-%s-%s/%s' %(teamname,keyname,micstarinput)
                        outputbucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)
                micdir='Micrographs'
                if os.path.exists('%s/s3out.log'%(outdir)):
                        os.remove('%s/s3out.log'%(outdir))
                #Check that it exists
		if bucketname.split('s3://')[-1][-1] != '/':
                	cmd='aws s3 ls %s/ > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
			subprocess.Popen(cmd,shell=True).wait()
                if bucketname.split('s3://')[-1][-1] == '/':
                        cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
                        subprocess.Popen(cmd,shell=True).wait()
		flagExist=False
                if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0:
                        flagExist=True
                os.remove('%s/s3out.log'%(outdir))
                if flagExist is False:
                        writeToLog('Error: Could not find specified s3 bucket %s. Exiting' %(bucketname.split('s3://')[-1]),'%s/run.err' %(outdir))
                        sys.exit()
                cmd='aws s3 ls %s/ > %s/s3out.log' %(outputbucketname.split('s3://')[-1],outdir)
		subprocess.Popen(cmd,shell=True).wait()
                if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0:
                        writeToLog("Error: Output aligned movies already exist %s/. Remove using aws_projects_remove_directory and re-submit." %(outputbucketname.split('s3://')[-1]),'%s/run.err' %(outdir))
                        sys.exit()
                if bucketname.split('s3://')[-1][-1] != '/':
                        cmd='aws s3 ls %s/ > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
                        subprocess.Popen(cmd,shell=True).wait()
                if bucketname.split('s3://')[-1][-1] == '/':
                        cmd='aws s3 ls %s/%s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
                        subprocess.Popen(cmd,shell=True).wait()
		origdir=micstar.split('/')[1].split('-')
		if origdir[0] == 'motioncorr':
			origdir[0]='MotionCorr'
		origdir='/'.join(origdir)	
		if os.path.exists('movies.star'):
                        os.remove('movies.star')
                micout=open('movies.star','w')
                micout.write('data_\n')
                micout.write('loop_\n')
                micout.write('_rlnMicrographMovieName\n')
                s3open=open('%s/s3out.log'%(outdir),'r')
                miccounter=1
		for s3 in s3open:
                        if s3.split()[0] == 'PRE':
                                continue
                        if s3.split()[-1] == '.tmp':
                                continue
			if s3.split()[-1].split('.')[-1] == 'mrcs':
                                micout.write('%s/%s/%s\n' %(origdir,micdir,s3.split()[-1].strip()))
				inputfilesize=s3.split()[-2].strip()
                		miccounter=miccounter+1
		s3open.close()
                micout.close()
                micstar='movies.star'
		sizeneeded='%.0f' %(math.ceil((float(inputfilesize)/1000000000)*miccounter*2.5))
	        actualsize='%.0f' %(math.ceil((float(inputfilesize)/1000000000)*miccounter*2.5))
		if sizeneeded>16000: 
			sizeneeded=16000
	if Es3_exist is False:
                writeToLog('Started upload of particle stacks to AWS on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
                if len(project) == 0:
                        Ebucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
                if len(project) > 0:
                        Ebucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,indirname)
                if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                        numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                        numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                Ebucketname=rclone_to_s3(extractDir,numCPUs*2.4,awsregion,key_ID,secret_ID,Ebucketname,Ebucketname,awsdir,project,'')
		#Ebucketname,micdir,origdir=rclone_to_s3(boxdir,numCPUs*2.4,awsregion,key_ID,secret_ID,Ebucketname,Ebucketname,awsdir,project)
                writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
	if s3_exist is True:
		microcol=1
        	symflag=0
	        samedir=0
		for line in open(micstar,'r'):
	                if len(line) < 40:
        	                continue
                	if len(line.split()[microcol-1].split('/')) == 0:
	                        dirtransfer=''
        	                origdir=''
                	        samedir=1
                        	mic=line.split()[microcol-1]
	                        miconly=mic.split('/')[-1]
                	if len(line.split()[microcol-1].split('/')) > 0:
                        	mic=line.split()[microcol-1]
	                        miconly=mic.split('/')[-1]
        	                origdir=mic.split(miconly)[0]
                	        if os.path.islink(mic) is True:
                        	        symdir=os.path.realpath(mic).split(miconly)[0]
                                	dirtransfer=symdir
        	                        symflag=1
                	        if os.path.islink(mic) is False:
                        	        dirtransfer=line.split()[microcol-1].split(miconly)[0]	
		micdir=dirtransfer
	
	writeToLog('Launching virtual machines ...','%s/run.out' %(outdir))

	#GEt number of movies
	moviecounter=0
	for mline in open(micstar,'r'): 
		if 'mrc' in mline: 
			moviecounter=moviecounter+1
	numMoviesPerInstance=math.ceil(moviecounter/numInstancesRequired)+1

	#Split up micstar
	count=0
        instancenum=0
        while count < moviecounter:
                icount=0
                if os.path.exists('%s_%i.star' %(micstar[:-5],instancenum)):
                        os.remove('%s_%i.star' %(micstar[:-5],instancenum))
                n1=open('%s_%i.star' %(micstar[:-5],instancenum),'w')
                n1.write('data_\n')
                n1.write('loop_\n')
                n1.write('_rlnMicrographMovieName\n')
                while icount < numMoviesPerInstance:
                        if icount >=moviecounter:
                                icount=icount+1
                                continue
                        n1.write('%s\n' %(linecache.getline(micstar,icount+count+1+3).strip()))
                        icount=icount+1
                instancenum=instancenum+1
                n1.close()
                count=count+int(numMoviesPerInstance)
	
	#Launch instance
	AMI='ami-5d26b83d'
	instanceNum=0
	'''
	while instanceNum < numInstancesRequired:
                #Launch instance
                if os.path.exists('%s/awslog_%i.log' %(outdir,instanceNum)):
                        os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                cmd='%s/launch_AWS_instance.py --AMI=%s --relion2 --instance=%s --availZone=%sa --noEBS > %s/awslog_%i.log' %(awsdir,AMI,instance,awsregion,outdir,instanceNum)
		subprocess.Popen(cmd,shell=True)
                instanceNum=instanceNum+1
                time.sleep(10)
        instanceNum=0
	instanceList=[]
        IPlist=[]
        instanceIDlist=[]
        while instanceNum < numInstancesRequired:
                isdone=0
                qfile='%s/awslog_%i.log'%(outdir,instanceNum)
                while isdone == 0:
                        r1=open(qfile,'r')
                        for line in r1:
                                if len(line.split()) == 2:
                                        if line.split()[0] == 'ID:':
                                                instanceList.append(line.split()[1])
                                                isdone=1
                        r1.close()
                        time.sleep(10)
                instanceID=subprocess.Popen('cat %s/awslog_%i.log | grep ID' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
                keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
                userIP=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()
                os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                IPlist.append(userIP)
                instanceIDlist.append(instanceID.strip())
                instanceNum=instanceNum+1
        
	writeToLog('Transferring data ...','%s/run.out' %(outdir))

	instanceNum=0
	while instanceNum < numInstancesRequired:
		#Create directories on AWS
		env.host_string='ubuntu@%s' %(IPlist[instanceNum])
		env.key_filename = '%s' %(keypair)

		#Format Raid0 drive on d2 instance
		exec_remote_cmd('sudo mdadm --create --verbose /dev/md0 --level=stripe --raid-devices=%i %s' %(numRaid,drives))
		exec_remote_cmd('sudo mkfs.ext4 -L MY_RAID /dev/md0')
		exec_remote_cmd('sudo mount LABEL=MY_RAID /data')
		exec_remote_cmd('sudo chmod 777 /data/')

		cmd='rsync -R -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s*  ubuntu@%s:/data/ > %s/rsync.log' %(keypair,boxbase,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()

		dirlocation='/data'
        	for entry in outdir.split('/'):
                	if len(entry.split('.star')) == 1:
				exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
	                        dirlocation=dirlocation+'/'+entry
		dirlocation='/data'
	        for entry in micstar.split('/'):
			if len(entry.split('.star')) == 1:
				exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
				dirlocation=dirlocation+'/'+entry
		locallocation=micstar.split('/')
		del locallocation[-1]
		locallocation='/'.join(locallocation)
		micInDir=dirlocation
		dirlocation='/data'
		for entry in extractDir.split('/'):
			exec_remote_cmd('mkdir /%s/%s/' %(dirlocation,entry))
			dirlocation=dirlocation+'/'+entry
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s_%i.star  ubuntu@%s:%s/ > %s/rsync.log' %(keypair,micstar[:-5],instanceNum,IPlist[instanceNum],micInDir,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		#Copy remote command to instance
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/../relion/relion_movie_extract_refine.py ubuntu@%s:/data/ > %s/rsync.log' %(keypair,awsdir,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ~/.rclone.conf ubuntu@%s:~/ > %s/rsync.log' %(keypair,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()
	
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/rclone ubuntu@%s:~/ > %s/rsync.log' %(keypair,awsdir,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		
		#Execute command
		relion_remote_cmd='relion_movie_extract_refine.py %s_%i.star %s /data/%s/Micrographs %f %s /data/%s "%s" %s %i' %(micstar[:-5],instanceNum,bucketname,origdir,math.ceil(mpi*2.4),Ebucketname.split('s3://')[-1],extractDir,relioncmdpre,outdir,instanceNum)
	        o2=open('run_awsRefine.job','w')
        	o2.write('#!/bin/bash\n')
	        o2.write('cd /data\n')
        	o2.write('./%s\n' %(relion_remote_cmd))
	        o2.close()
        	time.sleep(5)
		st = os.stat('run_awsRefine.job')
	        os.chmod('run_awsRefine.job', st.st_mode | stat.S_IEXEC)
        	time.sleep(5)
                subprocess.Popen(cmd,shell=True).wait()
		cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s run_awsRefine.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		time.sleep(5)
		cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null  -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "export PATH=/home/EM_Packages/relion2.0/build/bin:$PATH && export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:$LD_LIBRARY_PATH && export PATH=/bin/:$PATH && nohup ./run_awsRefine.job > /data/run.out 2> /data/run.err < /dev/null &"' %(keypair,IPlist[instanceNum])
        	time.sleep(5)
	        subprocess.Popen(cmd,shell=True)

		instanceNum=instanceNum+1

	writeToLog('Movie extraction submitted to the cloud...','%s/run.out' %(outdir))

	instanceNum=0
	outBucket=Ebucketname.split('s3://')[-1].split('/')
	del outBucket[-1]
	outBucket='/'.join(outBucket)+'/'+outdir.split('/')[0].lower()+'-'+outdir.split('/')[1]

	while instanceNum < numInstancesRequired: 
		isdone=0
		while isdone == 0:
			if os.path.exists('%s/s3check.log' %(outdir)): 
				os.remove('%s/s3check.log' %(outdir))
			cmd='aws s3 ls %s/ > %s/s3check.log' %(outBucket,outdir)
			subprocess.Popen(cmd,shell=True).wait()
			numlineslog=len(open('%s/s3check.log' %(outdir),'r').readlines())
			print numlineslog
			if numlineslog > 0: 
				readfile=open('%s/s3check.log' %(outdir),'r')
				for l in readfile: 
					print l
					if len(l) >0:		
						print 'particles_movie_%i.star' %(instanceNum) 
						print l.split()[-1]
						if l.split()[-1] == 'particles_movie_%i.star' %(instanceNum):
							isdone=1
							print 'done!!!!!!!!! particles_movie_%i.star' %(instanceNum)
			time.sleep(30)
		instanceNum=instanceNum+1
	time.sleep(30)
	
	writeToLog('Movie extraction finished! Beginning alignment of extracted movie-frame particles with 3D volume...','%s/run.out' %(outdir))

	for instanceID in instanceIDlist:
                cmd=subprocess.Popen('aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                subprocess.Popen(cmd,shell=True).wait()
                time.sleep(5)
        for instanceID in instanceIDlist:
                isdone=0
                while isdone == 0:
                        status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                        if status == 'terminated':
                                isdone=1
                        time.sleep(10)
        time.sleep(30)
	'''
	outBucket='rln-aws-leschziner-mike-oregon/empiar-10061/movierefine-job266/'

	instanceNum=0
	if os.path.exists('%s/awslog_%i.log' %(outdir,instanceNum)):
        	os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
        cmd='%s/launch_AWS_instance.py  --AMI=%s --relion2 --instance=%s --availZone=%sa --noEBS > %s/awslog_%i.log' %(awsdir,AMI,Refinstance,awsregion,outdir,instanceNum)
        subprocess.Popen(cmd,shell=True)
        time.sleep(10)
	instanceList=[]
	isdone=0
        qfile='%s/awslog_%i.log'%(outdir,instanceNum)
        while isdone == 0:
        	r1=open(qfile,'r')
                for line in r1:
                	if len(line.split()) == 2:
                        	if line.split()[0] == 'ID:':
                                	instanceList.append(line.split()[1])
                                        isdone=1
                r1.close()
                time.sleep(10)
        instanceID=subprocess.Popen('cat %s/awslog_%i.log | grep ID' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
        keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        userIP=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()
        os.remove('%s/awslog_%i.log' %(outdir,instanceNum))

        env.host_string='ubuntu@%s' %(userIP)
        env.key_filename = '%s' %(keypair)

        #Format Raid0 drive on d2 instance
        exec_remote_cmd('sudo mdadm --create --verbose /dev/md0 --level=stripe --raid-devices=%i %s' %(RefnumRaid,Refdrives))
        exec_remote_cmd('sudo mkfs.ext4 -L MY_RAID /dev/md0')
        exec_remote_cmd('sudo mount LABEL=MY_RAID /data')
        exec_remote_cmd('sudo chmod 777 /data/')

        cmd='rsync -R -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s*  ubuntu@%s:/data/ > %s/rsync.log' %(keypair,boxbase,userIP,outdir)
	subprocess.Popen(cmd,shell=True).wait()

        dirlocation='/data'
        for entry in outdir.split('/'):
        	if len(entry.split('.star')) == 1:
                	exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
        dirlocation='/data'
        for entry in micstar.split('/'):
        	if len(entry.split('.star')) == 1:
                	exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
        locallocation=micstar.split('/')
        del locallocation[-1]
        locallocation='/'.join(locallocation)
        micInDir=dirlocation
        dirlocation='/data'
        for entry in extractDir.split('/'):
   	     exec_remote_cmd('mkdir /%s/%s/' %(dirlocation,entry))
             dirlocation=dirlocation+'/'+entry
        #cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s_%i.star  ubuntu@%s:%s/ > %s/rsync.log' %(keypair,micstar[:-5],instanceNum,IPlist[instanceNum],micInDir,outdir)
        #subprocess.Popen(cmd,shell=True).wait()

        cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ~/.rclone.conf ubuntu@%s:~/ > %s/rsync.log' %(keypair,userIP,outdir)
	subprocess.Popen(cmd,shell=True).wait()

        cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/rclone ubuntu@%s:~/ > %s/rsync.log' %(keypair,awsdir,userIP,outdir)
	subprocess.Popen(cmd,shell=True).wait()

        #Execute command
	exec_remote_cmd('~/rclone copy rclonename:%s/ /data/%s/ --transfers %i' %(outBucket,outdir,Refmpi))
	exec_remote_cmd('~/rclone copy rclonename:%s/ /data/%s/ --transfers %i '%(Ebucketname.split('s3://')[-1],extractDir,Refmpi))

	#Combine multiple particles_movie.star files into a single particles_movie.star file 
	starfilelist='"'
	instanceNum=0
	while instanceNum < numInstancesRequired:
		starfilelist=starfilelist+'/data/%s/particles_movie_%i.star ' %(outdir,instanceNum)
		instanceNum=instanceNum+1
	starfilelist=starfilelist+' "'
	exec_remote_cmd('relion_star_combine --i %s --o /data/%s/particles_movie.star' %(starfilelist,outdir))

	if Refmpi == 128: 
		UseMPI=20
		UseJ=6
	if Refmpi == 36: 
		UseMPI=6
		UseJ=6
	relion_remote_cmd='mpirun -np %i /home/EM_Packages/relion2.0/build/bin/relion_refine_mpi %s --j %i' %(UseMPI,relioncmdrefine,UseJ)

        o2=open('run_awsRefine.job','w')
        o2.write('#!/bin/bash\n')
        o2.write('cd /data\n')
        o2.write('%s\n' %(relion_remote_cmd))
        o2.close()
        st = os.stat('run_awsRefine.job')
        os.chmod('run_awsRefine.job', st.st_mode | stat.S_IEXEC)
        cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" run_awsRefine.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,userIP,outdir)
        subprocess.Popen(cmd,shell=True).wait()
	
	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null  -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:$LD_LIBRARY_PATH && nohup ./run_awsRefine.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,userIP,outdir,outdir)
        time.sleep(5)
	print cmd
	sys.exit()
	subprocess.Popen(cmd,shell=True)


	nextIt=int(boxdir[-3:])

	isdone=0
        while isdone == 0:
                cmd='rsync --max-size=0.2G -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(keypair,userIP,outdir,outdir,outdir)
                subprocess.Popen(cmd,shell=True).wait()
                if os.path.exists('%s_it%03i_data.star' %(outdirRefFull,nextIt)):
                        isdone=1
                time.sleep(10)
        time.sleep(30)

	writeToLog('Movie-frame particle alignment to 3D model finished. Shutting everything down...', '%s/run.out' %(outdir))

	cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir)
        subprocess.Popen(cmd,shell=True).wait()

	isdone=0
        while isdone == 0:
  	      status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
              if status == 'terminated':
          	    isdone=1
              time.sleep(10)

	now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
                cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
                cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
        cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(boxdir,outdir,float(deltaHr)*float(cost))
        subprocess.Popen(cmd,shell=True).wait()

	#Update .aws_relion
        if os.path.exists('.aws_relion_tmp'):
                os.remove('.aws_relion_tmp')
        if os.path.exists('.aws_relion'):
                shutil.move('.aws_relion','.aws_relion_tmp')
                tmpout=open('.aws_relion','w')
                for line in open('.aws_relion_tmp','r'):
                        if line.split()[0] == micstar:
                                continue
			if line.split()[0] == outdir:
				continue
                        tmpout.write(line)
		tmpout.close()
                os.remove('.aws_relion_tmp')

        cmd='echo "%s     %s      %s" >> .aws_relion' %(micstar,bucketname,'-')
	subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "%s     %s      %s" >> .aws_relion' %(outdir,bucketname,'-')
        subprocess.Popen(cmd,shell=True).wait()

	if len(project) > 0:
                projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)

                cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                if os.path.exists('.aws_relion_project_info'):
                        cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

		#Remove all micrographs in bucket already
		cmd='aws s3 rm s3://%s/%s/ --recursive > %s/s3tmp.log' %(projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 sync %s/ s3://%s/%s > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                guilist=glob.glob('.gui*')
                for gui in guilist:
                        cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()
                if os.path.exists('%s/s3tmp.log'%(outdir)):
                        os.remove('%s/s3tmp.log'%(outdir))

	#Cleanup
	if os.path.exists('awslog.log'):
		os.remove('awslog.log')
	if os.path.exists('awsebs.log'):
		os.remove('awsebs.log')
	if os.path.exists('rsync.log'):
		os.remove('rsync.log')

#==============================
def relion_preprocess_mpi(project):

	#Get relion command and input options
	relioncmd,micstar,boxdir,outdir=getCMDpreprocess(infile)

	#Parse relion command to only include input options, removing any mention of 'gpu' or j threads in command
	relioncmd=parseCMDpreprocess(relioncmd)

	#Choose instance type
	instance='m4.4xlarge'
        mpi=16
        cost=0.862

	#Get AWS region from aws_init.sh environment variable
	awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	writeToLog('Booting up virtual machine %s on AWS in availability zone %sa' %(instance,awsregion), '%s/run.out' %(outdir))

	#Get AWS CLI directory location
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
		print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
		sys.exit()

	#Get AWS ID
	AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

	#Get AWS CLI directory location
	awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
		print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
		sys.exit()

	#.aws_relion will Have: [particledir] [s3 bucket name] [ebs volume]
	ebs_exist=False
	s3_exist=False
	bucketname=''
	if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
                        if line.split()[0].strip().replace('//','/') == micstar.strip().replace('//','/'):
                                bucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log'%(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1].replace('//','/'),outdir)
				subprocess.Popen(cmd,shell=True).wait()
                                if len(open('%s/s3out.log'%(outdir),'r').readlines()) > 0:
                                        s3_exist=True
	keyname=keypair.split('/')[-1].split('.pem')[0]
        keyname=keyname.split('_')
        keyname='-'.join(keyname)
        outdirname=outdir.split('/')
        if len(outdirname[-1]) == 0:
                del outdirname[-1]
        outdirname='-'.join(outdirname)
        outdirname=outdirname.lower().strip()
        keyname=keyname.lower().strip()
        project=project.strip()
	indirname=micstar.split('/')
	del indirname[-1]
	indirname='-'.join(indirname)
	indirname=indirname.lower().strip()

	#Upload data to S3
	if s3_exist is False:
		writeToLog('Started upload to AWS on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
		if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
                if len(project) > 0:
                        bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,indirname)
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                	numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
	                numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		bucketname,micdir,origdir=rclone_to_s3_preprocess(micstar,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project)
		writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
	if s3_exist is True:
		microcol=1
        	symflag=0
	        samedir=0
		for line in open(micstar,'r'):
	                if len(line) < 40:
        	                continue
                	if len(line.split()[microcol-1].split('/')) == 0:
	                        dirtransfer=''
        	                origdir=''
                	        samedir=1
                        	mic=line.split()[microcol-1]
	                        miconly=mic.split('/')[-1]
                	if len(line.split()[microcol-1].split('/')) > 0:
                        	mic=line.split()[microcol-1]
	                        miconly=mic.split('/')[-1]
        	                origdir=mic.split(miconly)[0]
                	        if os.path.islink(mic) is True:
                        	        symdir=os.path.realpath(mic).split(miconly)[0]
                                	dirtransfer=symdir
        	                        symflag=1
                	        if os.path.islink(mic) is False:
                        	        dirtransfer=line.split()[microcol-1].split(miconly)[0]	
		micdir=dirtransfer
	inputfilesize=subprocess.Popen('du %s' %(micdir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-2]
	sizeneeded='%.0f' %(math.ceil((float(inputfilesize)*3)/1000000))
       	actualsize='%.0f' %(math.ceil((float(inputfilesize)/1000000)))

	if ebs_exist is False:
		writeToLog('Creating data storage drive ...','%s/run.out' %(outdir))
        	#Create EBS volume
        	if os.path.exists('%s/awsebs.log' %(outdir)) :
               		os.remove('%s/awsebs.log'%(outdir))
        	cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%s"'%(awsdir,int(sizeneeded),awsregion,teamname,boxdir)+'> %s/awsebs.log'%(outdir)
        	subprocess.Popen(cmd,shell=True).wait()

        	#Get volID from logfile
        	volID=linecache.getline('%s/awsebs.log'%(outdir),5).split('ID: ')[-1].split()[0]

	writeToLog('Launching virtual machine ...','%s/run.out' %(outdir))

	#Launch instance
	if os.path.exists('%s/awslog.log'%(outdir)):
		os.remove('%s/awslog.log'%(outdir))
	cmd='%s/launch_AWS_instance.py --relion2 --instance=%s --availZone=%sa --volume=%s > %s/awslog.log' %(awsdir,instance,awsregion,volID,outdir)
	subprocess.Popen(cmd,shell=True).wait()
	#Get instance ID, keypair, and username:IP
	now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute
	instanceID=subprocess.Popen('cat %s/awslog.log | grep ID' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1].strip()
        keypair=subprocess.Popen('cat %s/awslog.log | grep ssh' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        userIP=subprocess.Popen('cat %s/awslog.log | grep ssh' %(outdir), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()

	#Create directories on AWS
	env.host_string='ubuntu@%s' %(userIP)
	env.key_filename = '%s' %(keypair)
	dirlocation='/data'
	for entry in boxdir.split('/'):
		exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
		dirlocation=dirlocation+'/'+entry


	writeToLog('Transferring data ...','%s/run.out' %(outdir))

	cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s  ubuntu@%s:%s/ > %s/rsync.log' %(keypair,boxdir,userIP,dirlocation,outdir)
        subprocess.Popen(cmd,shell=True).wait()

	#Make output directories
	dirlocation='/data'
        for entry in outdir.split('/'):
                if len(entry.split('.star')) == 1:
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
	dirlocation='/data'
        for entry in micstar.split('/'):
		if len(entry.split('.star')) == 1:
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
			dirlocation=dirlocation+'/'+entry
	locallocation=micstar.split('/')
	del locallocation[-1]
	locallocation='/'.join(locallocation)

	micInDir=dirlocation
	cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/  ubuntu@%s:%s/ > %s/rsync.log' %(keypair,locallocation,userIP,micInDir,outdir)
        subprocess.Popen(cmd,shell=True).wait()

	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
		numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
	if ebs_exist is False:
		s3_to_ebs(userIP,keypair,bucketname,'/data/%s/' %(origdir),'%s/rclone' %(awsdir),key_ID,secret_ID,awsregion,math.ceil(mpi*2.4))

	relion_remote_cmd='mpirun -np %i /home/EM_Packages/relion2.0/build/bin/relion_preprocess_mpi %s' %(mpi,relioncmd)

	o2=open('run_aws.job','w')
	o2.write('#!/bin/bash\n')
	o2.write('cd /data\n')
	o2.write('%s\n' %(relion_remote_cmd))
	o2.close()
	st = os.stat('run_aws.job')
	os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
	cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,userIP,outdir)
	subprocess.Popen(cmd,shell=True).wait()
	
	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null  -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:$LD_LIBRARY_PATH && nohup ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,userIP,outdir,outdir)
	time.sleep(5)
	subprocess.Popen(cmd,shell=True)

	writeToLog('Job submitted to the cloud...','%s/run.out' %(outdir))

	#cmd='rsync -q --ignore-errors -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/run.out ubuntu@%s:%s/ > %s/rsync.log' %(keypair,outdir,userIP,outdir,outdir)
	subprocess.Popen(cmd,shell=True).wait()

	isdone=0
	while isdone == 0:
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(keypair,userIP,outdir,outdir,outdir)
		subprocess.Popen(cmd,shell=True).wait()
		if os.path.exists('%s/particles.star' %(outdir)):
			isdone=1
		time.sleep(10)

	time.sleep(30)

	writeToLog('Job finished!','%s/run.out' %(outdir))

	cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir)
        subprocess.Popen(cmd,shell=True).wait()

	now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
                cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
                cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
        cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(boxdir,outdir,float(deltaHr)*float(cost))
        subprocess.Popen(cmd,shell=True).wait()

	#Update .aws_relion
        if os.path.exists('.aws_relion_tmp'):
                os.remove('.aws_relion_tmp')
        if os.path.exists('.aws_relion'):
                shutil.move('.aws_relion','.aws_relion_tmp')
                tmpout=open('.aws_relion','w')
                for line in open('.aws_relion_tmp','r'):
                        if line.split()[0] == micstar:
                                continue
			if line.split()[0] == outdir:
				continue
                        tmpout.write(line)
		tmpout.close()
                os.remove('.aws_relion_tmp')

        cmd='echo "%s     %s      %s" >> .aws_relion' %(micstar,bucketname,volID)
	subprocess.Popen(cmd,shell=True).wait()

	cmd='echo "%s     %s      %s" >> .aws_relion' %(outdir,bucketname,volID)
        subprocess.Popen(cmd,shell=True).wait()

	if len(project) > 0:
                projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)

                cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                if os.path.exists('.aws_relion_project_info'):
                        cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

		#Remove all micrographs in bucket already
		cmd='aws s3 rm s3://%s/%s/ --recursive > %s/s3tmp.log' %(projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 sync %s/ s3://%s/%s > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                guilist=glob.glob('.gui*')
                for gui in guilist:
                        cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()
                if os.path.exists('%s/s3tmp.log'%(outdir)):
                        os.remove('%s/s3tmp.log'%(outdir))

	#Cleanup
	if os.path.exists('awslog.log'):
		os.remove('awslog.log')
	if os.path.exists('awsebs.log'):
		os.remove('awsebs.log')
	if os.path.exists('rsync.log'):
		os.remove('rsync.log')

#=============================
def relion_run_ctffind(project):

	relioncmd,micstar,outdir,ifGctf=getCMDctf(infile)
	relioncmd,downloadbinned=parseCMDctf(relioncmd)
	#Get AWS region from aws_init.sh environment variable
        awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()
	if ifGctf is False:
		writeToLog('Error: Only Gctf is configured at this time. Please select and submit job again', '%s/run.err' %(outdir))
		sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()

        writeToLog('Starting relion job in the cloud...','%s/run.out' %(outdir))

	#.aws_relion will Have: [particledir] [s3 bucket name] [ebs volume]
        ebs_exist=False
        s3_exist=False
        bucketname=''
	otherbucketDirName=''
        if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
			if line.split()[0].strip() == micstar.strip():
				bucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log' %(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
				subprocess.Popen(cmd,shell=True).wait()
				if len(open('%s/s3out.log'%(outdir),'r').readlines()) > 0: 
					s3_exist=True
	keyname=keypair.split('/')[-1].split('.pem')[0]
        keyname=keyname.split('_')
        keyname='-'.join(keyname)
        outdirname=outdir.split('/')
        if len(outdirname[-1]) == 0:
                del outdirname[-1]
        outdirname='-'.join(outdirname)
        outdirname=outdirname.lower().strip()
        keyname=keyname.lower().strip()
        project=project.strip()
        #Upload data to S3
	if s3_exist is False:
                writeToLog('Started micrograph upload on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
                if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time()) 
                if len(project) > 0: 
			bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                	numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                	numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
			numCPUs=1
		bucketname,micdir,otherbucket,otherbucketDirName=rclone_to_s3_mics(micstar,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project)
		writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))

	#Get number of movies
        m1=open(micstar,'r')
        movieCounter=0
        for line in m1:
                movieCounter=movieCounter+1
        m1.close()
        movieCounter=movieCounter-3

        if movieCounter > 500:
                instance='p2.8xlarge'
                mpi=32
                gpu=8
                cost=7.2
		numInstancesRequired=1
        if movieCounter <= 500:
	        instance='p2.xlarge'
                numInstancesRequired=1
                mpi=4
                gpu=1
                cost=0.9
	writeToLog('Booting up %i x %s virtual machines on AWS to estimate CTF with Gctf in availability zone %sa' %(numInstancesRequired,instance,awsregion), '%s/run.out' %(outdir))

        instanceNum=0
        ebsVolList=[]
        instanceList=[]
        writeToLog('Creating data storage drive(s) ...','%s/run.out' %(outdir))

	#Get first mic from micstar
	flag=0 
	maximum=60
	counter=1
	while counter <= maximum:
		line=linecache.getline(micstar,counter)
		if len(line.split())>0: 
			if line.split()[0] == '_rlnMicrographName': 
				if len(line.split()) == 2: 
					colnum=int(line.split()[-1].split('#')[-1])
				if len(line.split()) == 1:
					colnum=1 
		counter=counter+1 
	counter=1
	while counter <=maximum: 
		line=linecache.getline(micstar,counter).strip()
		if len(line)>0: 
			if line[0] != '_':
				if line[-1] != '_':
					if flag == 0: 
						micname=line.split()[colnum-1]
						flag=1
		counter=counter+1
	sizeneeded=math.ceil((float(subprocess.Popen('du %s' %(micname),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[0])/1000000)*movieCounter*4)	
	if sizeneeded < 3: 
		sizeneeded=5

	newmicname=[]
	namelist=micname.split('/')
	for name in namelist: 
		if len(name)==0: 
			continue
		newmicname.append(name)

	if len(newmicname) == 4: 
		extraDir=newmicname[2]
	else:
		extraDir=''
	'''	
	#Get individual file size, multiply by all for downloading all movies
	if len(otherbucketDirName) == 0:
		print 'aws s3api list-objects --bucket %s --output json --query "[sum(Contents[].Size), length(Contents[])]"' %(bucketname.split('s3://')[-1])
		s3out=subprocess.Popen('aws s3api list-objects --bucket %s --output json --query "[sum(Contents[].Size), length(Contents[])]"' %(bucketname.split('s3://')[-1]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		sizeneeded=math.ceil(float(s3out.split()[1].strip(','))//1000000000)*5
		if sizeneeded <3:
			sizeneeded=5
	if len(otherbucketDirName) > 0:
		s3out=subprocess.Popen('aws s3api list-objects --bucket %s-mic --output json --query "[sum(Contents[].Size), length(Contents[])]"' %(bucketname.split('s3://')[-1]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                sizeneeded=math.ceil(float(s3out.split()[1].strip(','))//1000000000)*5
                if sizeneeded <3:
                        sizeneeded=5
	'''
	while instanceNum < numInstancesRequired:
                #Create EBS volume
               	if os.path.exists('%s/awsebs_%i.log' %(outdir,instanceNum)) :
                        os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
               	cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%s"'%(awsdir,int(sizeneeded),awsregion,teamname,micstar)+'> %s/awsebs_%i.log' %(outdir,instanceNum)
		subprocess.Popen(cmd,shell=True).wait()
               	#Get volID from logfile
               	volID=linecache.getline('%s/awsebs_%i.log' %(outdir,instanceNum),5).split('ID: ')[-1].split()[0]
               	time.sleep(10)
                os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
                ebsVolList.append(volID)
                instanceNum=instanceNum+1

	instanceNum=0
        writeToLog('Launching virtual machine(s) ... usually requires 2 - 5 minutes for initialization','%s/run.out' %(outdir))
        while instanceNum < numInstancesRequired:
                #Launch instance
                if os.path.exists('%s/awslog_%i.log' %(outdir,instanceNum)):
                        os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                cmd='%s/launch_AWS_instance.py --relion2 --instance=%s --availZone=%sa --volume=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,ebsVolList[instanceNum],outdir,instanceNum)
                subprocess.Popen(cmd,shell=True)
                instanceNum=instanceNum+1
                time.sleep(10)
        instanceNum=0
        IPlist=[]
        instanceIDlist=[]
        while instanceNum < numInstancesRequired:
                isdone=0
                qfile='%s/awslog_%i.log'%(outdir,instanceNum)
                while isdone == 0:
                        r1=open(qfile,'r')
                        for line in r1:
                                if len(line.split()) == 2:
                                        if line.split()[0] == 'ID:':
                                                instanceList.append(line.split()[1])
                                                isdone=1
                        r1.close()
                        time.sleep(10)
                instanceID=subprocess.Popen('cat %s/awslog_%i.log | grep ID' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
	        keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
        	userIP=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()
                os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                IPlist.append(userIP)
                instanceIDlist.append(instanceID.strip())
                instanceNum=instanceNum+1

	now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute

        instanceNum=0
        env.key_filename = '%s' %(keypair)

        writeToLog('Submitting job to the cloud...','%s/run.out' %(outdir))

	#Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if os.path.exists('%s/.rclone.conf' %(homedir)):
                os.remove('%s/.rclone.conf' %(homedir))

        r1=open('%s/.rclone.conf' %(homedir),'w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(key_ID))
        r1.write('secret_access_key = %s\n' %(secret_ID))
        r1.write('region = %s\n' %(awsregion))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(awsregion))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

        while instanceNum < numInstancesRequired:
		env.host_string='ubuntu@%s' %(IPlist[instanceNum])
		othername=''
		if len(otherbucketDirName) > 0:
			counter=0
			dirlocation='/data'
			otherfactor=len(otherbucketDirName.split('/'))
			if otherfactor == 1:
				otherfactor=0
			if otherfactor > 1:
				otherfactor=1
			while counter <= len(otherbucketDirName.split('/'))-otherfactor:
                        	entry=otherbucketDirName.split('/')[counter]
				exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
        	                dirlocation=dirlocation+'/'+entry
	                        counter=counter+1
			othername=dirlocation
                #Create directories on AWS
                dirlocation='/data'
                counter=0
                while counter < len(micstar.split('/'))-1:
                        entry=micstar.split('/')[counter]
                        exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
                        counter=counter+1
                if len(extraDir)>0:
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,extraDir))
		indirlocation=dirlocation
                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,micstar,IPlist[instanceNum],dirlocation,outdir)
                subprocess.Popen(cmd,shell=True).wait()

		#Make output directories
                dirlocation='/data'
                counter=0
                while counter < len(outdir.split('/'))-1:
                        entry=outdir.split('/')[counter]
                        exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
                        counter=counter+1
                cmd='rsync -avzur -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/*  ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,outdir,IPlist[instanceNum],dirlocation,outdir)
		subprocess.Popen(cmd,shell=True).wait()
                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/rclone ubuntu@%s:~/'%(keypair,awsdir,IPlist[instanceNum])
                subprocess.Popen(cmd,shell=True).wait()

                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ~/.rclone.conf ubuntu@%s:~/'%(keypair,IPlist[instanceNum])
                subprocess.Popen(cmd,shell=True).wait()
		#print 'two'
		micdirlocation=indirlocation
		cloudpath='/data/'+outdir
		#Create exclude list: any mrc/mrcs in 'main' directory, and then any _movie.* in Micrographs
		if os.path.exists('excludelist233.txt'): 
			os.remove('excludelist233.txt')
		if len(extraDir)>0:
			micdirlocation=micdirlocation+'/'+extraDir
		exec_remote_cmd('~/rclone sync rclonename:%s %s --max-size 1G --quiet --transfers %i' %(bucketname.split('s3://')[-1],micdirlocation,mpi))
		if len(otherbucketDirName) > 0:
			exec_remote_cmd('~/rclone sync rclonename:%s-mic %s --quiet --transfers %i' %(bucketname.split('s3://')[-1],othername,mpi))

		if gpu  == 1:
			relion_remote_cmd='/home/EM_Packages/relion2.0/build/bin/relion_run_ctffind %s --gpu --gctf_exe /home/EM_Packages/Gctf_v0.50/bin/Gctf-v0.50_sm_30_cu7.5_x86_64' %(relioncmd)
		if gpu > 1:
			relion_remote_cmd='mpirun -np %i /home/EM_Packages/relion2.0/build/bin/relion_run_ctffind_mpi %s --gpu --gctf_exe /home/EM_Packages/Gctf_v0.50/bin/Gctf-v0.50_sm_30_cu7.5_x86_64' %(gpu,relioncmd)
	        o2=open('run_aws.job','w')
	        o2.write('#!/bin/bash\n')
	        o2.write('cd /data\n')
	        o2.write('%s\n' %(relion_remote_cmd))
	        o2.close()
        	st = os.stat('run_aws.job')
	        os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
		cmd='rsync --ignore-errors -avzu -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,IPlist[instanceNum],outdir)
	        subprocess.Popen(cmd,shell=True).wait()
		#print 'three'
        	cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib::/usr/local/cuda/lib64:$LD_LIBRARY_PATH && nohup ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,IPlist[instanceNum],outdir,outdir)
		subprocess.Popen(cmd,shell=True)

                instanceNum=instanceNum+1

	#cmd='rsync --ignore-errors  -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/run.out ubuntu@%s:%s/ > %s/rsync.log' %(keypair,outdir,IPlist[0],outdir,outdir)
	#subprocess.Popen(cmd,shell=True).wait()
        isdone=0
        while isdone == 0:
                cmd='rsync -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/run.* %s/ > %s/rsync.log' %(keypair,IPlist[0],outdir,outdir,outdir)
		subprocess.Popen(cmd,shell=True).wait()
                #print 'five'
		#print cmd
		#Check if job was specified to be killed
                isdone=check_and_kill_job('%s/note.txt' %(outdir),IPlist[0],keypair)
		testDone=subprocess.Popen('cat %s/run.out  | grep Done!' %(outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		if len(testDone) > 0:
			isdone=1
                time.sleep(10)
        time.sleep(30)

        writeToLog('Job finished!','%s/run.out' %(outdir))

	cmd='rsync --no-links -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(keypair,IPlist[0],outdir,outdir,outdir)
	subprocess.Popen(cmd,shell=True).wait()

	#Remove all .mrc files that now have a broken link
	for mrc in glob.glob('%s/Micrographs/*.mrc' %(outdir)):
		os.remove(mrc)

	for instanceID in instanceIDlist:
                #Kill all instances
		cmd=subprocess.Popen('aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                subprocess.Popen(cmd,shell=True).wait()
		time.sleep(5)
	for instanceID in instanceIDlist:
                isdone=0
                while isdone == 0:
                        status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                        if status == 'terminated':
                                isdone=1
                        time.sleep(10)
        time.sleep(30)
        #for volID in ebsVolList:
        #        cmd='%s/kill_volume.py %s > %s/awslog.log' %(awsdir,volID,outdir)
        #        subprocess.Popen(cmd,shell=True).wait()

        now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
                cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
                cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
        cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(micstar,outdir,float(deltaHr)*float(cost)*numInstancesRequired)
        subprocess.Popen(cmd,shell=True).wait()

	#Update .aws_relion
        if os.path.exists('.aws_relion_tmp'):
                os.remove('.aws_relion_tmp')
        if os.path.exists('.aws_relion'):
                shutil.move('.aws_relion','.aws_relion_tmp')
                tmpout=open('.aws_relion','w')
                for line in open('.aws_relion_tmp','r'):
                        tmpout.write(line)
                tmpout.close()
                os.remove('.aws_relion_tmp')
        cmd='echo "%s/micrographs_ctf.star     %s      ---" >> .aws_relion' %(outdir,bucketname)
        subprocess.Popen(cmd,shell=True).wait()
        if len(project) > 0:
                projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)
                cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                if os.path.exists('.aws_relion_project_info'):
                        cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 sync %s/ s3://%s/%s > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                guilist=glob.glob('.gui*')
                for gui in guilist:
                        cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()
		if os.path.exists('%s/s3tmp.log'%(outdir)): 
			os.remove('%s/s3tmp.log' %(outdir))

	if os.path.exists('%s/rsync.log' %(outdir)):
                os.remove('%s/rsync.log' %(outdir))
        moviestarlist=glob.glob('movies*.star')
        for moviestar in moviestarlist:
                if os.path.exists(moviestar):
                        os.remove(moviestar)
        if os.path.exists('run_aws.job'):
                os.remove('run_aws.job')
#==============================
def checkStatusInstances(instanceID,keypair,IPaddress,outdir):

	SysStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
        InsStatus=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]

	if SysStatus != 'ok' or InsStatus != 'ok': 
		print 'Instance %s lost connection. Rebooting and relaunching' %(instanceID)
		#Something happened to teh instance. Need to reboot and relaunch motioncor alignment 
		cmd='aws ec2 reboot-instances --instance-ids %s > tmp.log' %(instanceID)
		subprocess.Popen(cmd,shell=True).wait()		

		Status='init'
        	while Status != 'running':
 	       		Status=subprocess.Popen('aws ec2 describe-instances --instance-id %s --query "Reservations[*].Instances[*].{State:State}" | grep Name' %(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
               		if Status != 'running':
	               		time.sleep(10)
        	SysStatuscheck='init'
        	InsStatuscheck='init'

        	while SysStatuscheck != 'ok' and InsStatuscheck != 'ok':
        		SysStatuscheck=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].SystemStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                	InsStatuscheck=subprocess.Popen("aws ec2 describe-instance-status --instance-id %s --query 'InstanceStatuses[*].InstanceStatus.{SysCheck:Status}'|grep SysCheck" %(InstanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                	time.sleep(4)
	
		#Relaunch job
		launchcmd='ssh  -o "StrictHostKeyChecking no" -q -n -f -i %s ubuntu@%s "export PATH=/home/EM_Packages/relion2.0/build/bin:$PATH && export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH && ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,IPaddress,outdir,outdir)
		subprocess.Popen(launchcmd,shell=True)
		

#==============================
def relion_run_motioncorr(project):
	maxm4=5
	maxp28=8
	
	relioncmd,micstar,outdir,gainref,movieAlignType,ifMotionCor2,savemovies,angpix=getCMDmovie(infile)
	#Parse relion command to only include input options, removing any mention of 'gpu' or tick marks
        relioncmd,downloadBinnedOnly=parseCMDmovie(relioncmd)
        #Get AWS region from aws_init.sh environment variable
        awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

	if movieAlignType == 'unblur': 
		writeToLog('Unblur movie alignments are currently not supported. Please select motioncorr or motioncor2 and resbumit.','%s/run.err' %(outdir))
		sys.exit()

	#Check that all dose weighting parametser are specified
	errormessage,doseWeight=checkDoseInputs(infile)
	if len(errormessage)>0: 
		writeToLog('Error: %s' %(errormessage),'%s/run.err' %(outdir))
		sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        reliondir=subprocess.Popen('echo $AWS_RELION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
	if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()
	if len(reliondir) == 0: 
		print 'Error: Could not find AWS relion directory specified as $AWS_RELION. Please set this environmental variable and try again.'	
		sys.exit()
	writeToLog('Starting relion job in the cloud...','%s/run.out' %(outdir))

	#.aws_relion will Have: [particledir] [s3 bucket name] [ebs volume]
        ebs_exist=False
        s3_exist=False
        bucketname=''
        if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
                        if line.split()[0] == micstar:
                                bucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log' %(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls > %s/s3out.log' %(outdir)
                                subprocess.Popen(cmd,shell=True).wait()
                                for line in open('%s/s3out.log'%(outdir),'r'):
                                        if line.split()[-1] == bucketname.split('s3://')[-1]:
                                                s3_exist=True
                                os.remove('%s/s3out.log' %(outdir))
        keyname=keypair.split('/')[-1].split('.pem')[0]
	keyname=keyname.split('_')
	keyname='-'.join(keyname)
	outdirname=outdir.split('/')
	if len(outdirname[-1]) == 0:
		del outdirname[-1]
	outdirname='-'.join(outdirname)
	outdirname=outdirname.lower().strip()
	keyname=keyname.lower().strip()
	project=project.strip()
	#Upload data to S3
        if s3_exist is False and len(micstar.split('s3-')) == 1:
                writeToLog('Started movie upload on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
                if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
                if len(project) > 0:
			bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                	numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                	numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		bucketname,micdir,origdir=rclone_to_s3_movie(micstar,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project)
                writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
        	inputfilesize=subprocess.Popen('du %s' %(micdir), shell=True, stdout=subprocess.PIPE).stdout.read().split()[-2]
		outputbucketname=bucketname
	if len(micstar.split('s3-')) > 1:
		micstarinput=micstar.split('s3-')[-1]
		if micstarinput[-1] == '/': 
			micstarinput=micstarinput[:-1]
		if len(project) == 0:
                        bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())
		if len(project) > 0:
			bucketname='rln-aws-%s-%s/%s' %(teamname,keyname,micstarinput)
                        outputbucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)	
		micdir='Micrographs'
		if os.path.exists('%s/s3out.log'%(outdir)):
			os.remove('%s/s3out.log'%(outdir))
		#Check that it exists
		cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		flagExist=False
                if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0: 
			flagExist=True
		os.remove('%s/s3out.log'%(outdir))
		if flagExist is False:
			writeToLog('Error: Could not find specified s3 bucket %s. Exiting' %(bucketname.split('s3://')[-1]),'%s/run.err' %(outdir))
			sys.exit()
		cmd='aws s3 ls %s/Micrographs/ > %s/s3out.log' %(outputbucketname.split('s3://')[-1],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0: 
			writeToLog("Error: Output aligned movies already exist %s/Micrographs/. Remove using aws_projects_remove_directory and re-submit." %(outputbucketname.split('s3://')[-1]),'%s/run.err' %(outdir))
			sys.exit()
		cmd='aws s3 ls %s/ > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		if os.path.exists('movies.star'): 
			os.remove('movies.star')
		micout=open('movies.star','w')
		micout.write('data_\n')
		micout.write('loop_\n')
		micout.write('_rlnMicrographMovieName\n')
		s3open=open('%s/s3out.log'%(outdir),'r')
		for s3 in s3open:
			if s3.split()[0] == 'PRE':
				continue
			if s3.split()[-1] == '.tmp': 
				continue 
			if s3.split()[-1].split('.')[-1] == '.mrc' or s3.split()[-1].split('.')[-1] == '.mrcs' or s3.split()[-1] != gainref:
				micout.write('%s/%s\n' %(micdir,s3.split()[-1].strip()))
			if s3.split()[-1] == gainref:
				cmd='aws s3 cp s3://%s/%s .' %(bucketname,gainref)
				subprocess.Popen(cmd,shell=True).wait()
		s3open.close()
		micout.close()
		micstar='movies.star'
	#Get number of movies
        m1=open(micstar,'r')
        movieCounter=0
	for line in m1:
                movieCounter=movieCounter+1
        m1.close()
        movieCounter=movieCounter-3	
        #Choose instance type
        if movieAlignType == 'unblur':
                numInstancesRequired=math.ceil(movieCounter/32)
                if numInstancesRequired <=1:
			numInstancesRequired=1
		instance='r4.8xlarge'
                mpi=32
                cost=2.128
                gpu=0
		if numInstancesRequired > maxm4:
                        numInstancesRequired=5

        if movieAlignType == 'motioncorr':
                numInstancesRequired=int(math.ceil(movieCounter/16))
		if numInstancesRequired > maxp28:
                        numInstancesRequired=maxp28
		if numInstancesRequired >=1:
                	instance='p2.8xlarge'
                	mpi=32
                	gpu=8
                	cost=7.2
                if numInstancesRequired==0:
			instance='p2.xlarge'
                        mpi=4
                        gpu=1
                        cost=0.9
			numInstancesRequired=1
		if ifMotionCor2 is True:
                        movieAlignType = 'motioncor2'
		if movieCounter < 8:
			instance='p2.xlarge'
	        	numInstancesRequired=1
	        	gpu=1
        		mpi=4
		        cost=0.90
	if gpu > 0:
		ntasks=gpu
	if gpu == 0:
		ntasks=mpi-24
	sizeneeded=ntasks*50
	numMoviesPerInstance=math.ceil((movieCounter+1)/numInstancesRequired)
	count=0
	instancenum=0
	while count < movieCounter:
		icount=0
		if os.path.exists('%s_%i.star' %(micstar[:-5],instancenum)):
			os.remove('%s_%i.star' %(micstar[:-5],instancenum))
		n1=open('%s_%i.star' %(micstar[:-5],instancenum),'w')
		n1.write('data_\n')
                n1.write('loop_\n')
                n1.write('_rlnMicrographMovieName\n')
		while icount < numMoviesPerInstance:
			if icount >=movieCounter:
				icount=icount+1
				continue
			n1.write('%s\n' %(linecache.getline(micstar,icount+count+1+3).strip()))
			icount=icount+1
		instancenum=instancenum+1
		n1.close()
		count=count+int(numMoviesPerInstance)
	writeToLog('Booting up %i x %s virtual machines on AWS to align movies in availability zone %sa' %(numInstancesRequired,instance,awsregion), '%s/run.out' %(outdir))

	instanceNum=0
	ebsVolList=[]
	instanceList=[]
	writeToLog('Creating data storage drive(s) ...','%s/run.out' %(outdir))
	while instanceNum < numInstancesRequired:
                #Create EBS volume
                if os.path.exists('%s/awsebs_%i.log' %(outdir,instanceNum)) :
                        os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
		iosize=50*sizeneeded
		if iosize > 5000:
			iosize=5000
			
                cmd='%s/create_volume_IOPS.py %i %i %sa "rln-aws-tmp-%s-%s"'%(awsdir,int(sizeneeded),iosize,awsregion,teamname,micstar)+'> %s/awsebs_%i.log' %(outdir,instanceNum)
		subprocess.Popen(cmd,shell=True).wait()
                #Get volID from logfile
                volID=linecache.getline('%s/awsebs_%i.log' %(outdir,instanceNum),5).split('ID: ')[-1].split()[0]
		time.sleep(10)
		os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
		ebsVolList.append(volID)
		instanceNum=instanceNum+1
	instanceNum=0
	writeToLog('Launching virtual machine(s) ...','%s/run.out' %(outdir))
	while instanceNum < numInstancesRequired:
       	 	#Launch instance
        	if os.path.exists('%s/awslog_%i.log' %(outdir,instanceNum)):
                	os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
		cmd='%s/launch_AWS_instance.py --relion2 --instance=%s --availZone=%sa --volume=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,ebsVolList[instanceNum],outdir,instanceNum)
		subprocess.Popen(cmd,shell=True)
		instanceNum=instanceNum+1
       		time.sleep(10)
	instanceNum=0
        IPlist=[]
	instanceIDlist=[]
	while instanceNum < numInstancesRequired:
		isdone=0
		qfile='%s/awslog_%i.log'%(outdir,instanceNum)
		while isdone == 0:
			r1=open(qfile,'r')
			for line in r1:
				if len(line.split()) == 2:
					if line.split()[0] == 'ID:':
						instanceList.append(line.split()[1])
						isdone=1
			r1.close()
			time.sleep(10)
		instanceID=subprocess.Popen('cat %s/awslog_%i.log | grep ID' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
       		keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
	        userIP=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()
		os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
		IPlist.append(userIP)
		instanceIDlist.append(instanceID.strip())
		instanceNum=instanceNum+1

        now=datetime.datetime.now()
        startday=now.day
        starthr=now.hour
        startmin=now.minute

	instanceNum=0
	env.key_filename = '%s' %(keypair)

	writeToLog('Submitting movie alignment to the cloud...','%s/run.out' %(outdir))

	writeToLog('Waiting for movie alignment to finish. For %i movies on %i GPUs, this job will be finished in approximately %i minutes.' %(movieCounter,numInstancesRequired*gpu,int((5*movieCounter)/(numInstancesRequired*gpu))+4), '%s/run.out' %(outdir))

	while instanceNum < numInstancesRequired:
		#Create directories on AWS
        	env.host_string='ubuntu@%s' %(IPlist[instanceNum])
        	dirlocation='/data'
		counter=0
		while counter < len(micstar.split('/'))-1:
			entry=micstar.split('/')[counter]
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                	dirlocation=dirlocation+'/'+entry
			counter=counter+1
		indirlocation=dirlocation
        	cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s_%i.star ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,micstar[:-5],instanceNum,IPlist[instanceNum],dirlocation,outdir)
		subprocess.Popen(cmd,shell=True).wait()
        	#Make output directories
        	dirlocation='/data'
		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" -R %s ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,outdir,IPlist[instanceNum],dirlocation,outdir)
		subprocess.Popen(cmd,shell=True).wait()
		if gainref != -1:
			cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s ubuntu@%s:/data/ > %s/rsync.log' %(keypair,gainref,IPlist[instanceNum],outdir)
			subprocess.Popen(cmd,shell=True).wait()

		cmd='rsync -avzu -e "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/relion_movie_align.py ubuntu@%s:/data/ > %s/rsync.log' %(keypair,reliondir,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/rclone ubuntu@%s:~/'%(keypair,awsdir,IPlist[instanceNum])
		subprocess.Popen(cmd,shell=True).wait()
		cmd='scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ~/.rclone.conf ubuntu@%s:~/'%(keypair,IPlist[instanceNum])
		subprocess.Popen(cmd,shell=True).wait()
		
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
	                numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
		if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                	numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())

        	o2=open('run_aws.job','w')
		o2.write('cd /data\n')
		o2.write('/bin/chmod +x relion_movie_align.py\n')
		o2.write('./relion_movie_align.py %s_%i.star %i rclonename:%s/Micrographs %s %i %s "%s" "%s" %s %f %s' %(micstar[:-5],instanceNum,ntasks,outputbucketname.split('s3://')[-1],bucketname.split('s3://')[-1],ntasks*2,movieAlignType,relioncmd,gainref,outdir,angpix,savemovies))
        	o2.close()
        	st = os.stat('run_aws.job')
        	os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
        	cmd='rsync -avzu -e "ssh -q -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,IPlist[instanceNum],outdir)
		subprocess.Popen(cmd,shell=True).wait()

		launchcmd='ssh  -o StrictHostKeyChecking=no -q -n -f -i %s ubuntu@%s "export PATH=/usr/local/bin:/home/EM_Packages/relion2.0/build/bin:/bin/:$PATH && export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH && ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,IPlist[instanceNum],outdir,outdir)
		subprocess.Popen(launchcmd,shell=True)
		instanceNum=instanceNum+1

	os.makedirs('%s/Micrographs' %(outdir))
	#Start waiting script for when data are finished aligning
	miccount=0	
	if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
        	rclonepath='%s/rclone' %(awsdir)
        if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                rclonepath='%s/rclone_mac'%(awsdir)

        #Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if not os.path.exists('%s/.rclone.conf' %(homedir)):
        	r1=open('%s/.rclone.conf' %(homedir),'w')
	        r1.write('[rclonename]\n')
        	r1.write('type = s3\n')
	        r1.write('env_auth = false\n')
        	r1.write('access_key_id = %s\n' %(keyid))
	        r1.write('secret_access_key = %s\n' %(secretid))
        	r1.write('region = %s\n' %(region))
	        r1.write('endpoint = \n')
        	r1.write('location_constraint = %s\n' %(region))
	        r1.write('acl = authenticated-read\n')
        	r1.write('server_side_encryption = \n')
	        r1.write('storage_class = STANDARD\n')
        	r1.close()
	micdone=0
	lastonedone=0
	while micdone == 0:
		cmd='%s sync rclonename:%s/Micrographs/ %s/Micrographs/ --quiet --transfers %i --max-size 400M > rclone.log' %(rclonepath,outputbucketname.split('s3://')[-1],outdir,math.ceil(numCPUs*2.4))
                subprocess.Popen(cmd,shell=True).wait()
                os.remove('rclone.log')
		testmiclist='%s/Micrographs/*.mrc' %(outdir)
		numdone=0
		for testmic in glob.glob(testmiclist): 
			numdone=numdone+1				
		if numdone > lastonedone: 
			writeToLog('Finished %i out of %i total movies at %s...\n' %(numdone,movieCounter,time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
			lastonedone=numdone
		if numdone==movieCounter: 
			micdone=1
			writeToLog('Finished movie alignment!','%s/run.out' %(outdir))

		o9=open('%s/note.txt' %(outdir),'r')
                kill=0
                for line in o9:
	                if len(line.split()) > 0:
        	                if line.split()[0] == 'Kill':
                	                kill=1
                                if line.split()[0] == 'kill':
                                        kill=1
                if kill ==1:
                        micdone=1
			writeToLog('Abort signal specified.','%s/run.out' %(outdir))
                o9.close()

		time.sleep(5)

	writeToLog('Shutting down virtual machines...', '%s/run.out' %(outdir))
	#Write new output star file
	newmicsinoutdir=glob.glob('%s/Micrographs/*.mrc' %(outdir))
	dosemics=glob.glob('%s/Micrographs/*DW.mrc' %(outdir))
	newout=open('%s/corrected_micrographs.star' %(outdir),'w')
	newout.write('data_\n')
	newout.write('loop_\n')
        newout.write('_rlnMicrographName\n')
	for newmic in newmicsinoutdir:
		if 'DW.' in newmic: 
			continue
		newout.write('%s\n' %(newmic))
	newout.close()
	if len(dosemics)>0: 
		newout=open('%s/corrected_micrographs_doseWeighted.star' %(outdir),'w')
        	newout.write('data_\n')
	        newout.write('loop_\n')
        	newout.write('_rlnMicrographName\n')
	        for newmic in dosemics:
        	        newout.write('%s\n' %(newmic))
	        newout.close()	
	if os.path.exists('%s/awslog.log'%(outdir)): 
		os.remove('%s/awslog.log'%(outdir))
	for instanceID in instanceIDlist:
		cmd=subprocess.Popen('aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
                subprocess.Popen(cmd,shell=True).wait()
	for instanceID in instanceIDlist:
                isdone=0
                while isdone == 0:
                        status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
			if status == 'terminated':
                                isdone=1
                        time.sleep(10)
	time.sleep(30)
	for volID in ebsVolList:
		cmd='%s/kill_volume.py %s > %s/awslog.log' %(awsdir,volID,outdir)
		subprocess.Popen(cmd,shell=True).wait()

        now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
                cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
                cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
        cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(micstar,outdir,float(deltaHr)*float(cost)*numInstancesRequired)
        subprocess.Popen(cmd,shell=True).wait()

	#Update .aws_relion
        if os.path.exists('.aws_relion_tmp'):
                os.remove('.aws_relion_tmp')
        if os.path.exists('.aws_relion'):
                shutil.move('.aws_relion','.aws_relion_tmp')
                tmpout=open('.aws_relion','w')
                for line in open('.aws_relion_tmp','r'):
                        if line.split()[0] == micstar:
                                continue
			if line.split()[1] == bucketname:
				continue
                        tmpout.write(line)
		tmpout.close()
		os.remove('.aws_relion_tmp')
        cmd='echo "%s     %s      ---" >> .aws_relion' %(micstar,bucketname)
        subprocess.Popen(cmd,shell=True).wait()
	cmd='echo "%scorrected_micrographs.star     %s/Micrographs      ---" >> .aws_relion' %(outdir,bucketname)
        subprocess.Popen(cmd,shell=True).wait()
	if len(dosemics)>0:
		cmd='echo "%scorrected_micrographs_doseWeighted.star     %s      ---" >> .aws_relion' %(outdir,bucketname)
		subprocess.Popen(cmd,shell=True).wait()
	if len(project) > 0:
		projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)
		cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		if os.path.exists('.aws_relion_project_info'): 
			cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
			subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp %scorrected_micrographs.star s3://%s/%s/ > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp %sjob_pipeline.star s3://%s/%s/ > %s/s3tmp.log' %(outdir,projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp %srun.out s3://%s/%s/ > %s/s3tmp.log' %(outdir,projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp %sdefault_pipeline.star s3://%s/%s/ > %s/s3tmp.log' %(outdir,projectbucket,outdirname,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		guilist=glob.glob('.gui*')
		for gui in guilist: 
			cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
			subprocess.Popen(cmd,shell=True).wait() 

		indir=micstar.split('/')
		del indir[-1]
		indirbucket='-'.join(indir).lower()
		indir='/'.join(indir)
		cmd='aws s3 sync %s s3://%s/%s/ > %s/s3tmp.log' %(indir,projectbucket,indirbucket,outdir)
		subprocess.Popen(cmd,shell=True).wait()

	if os.path.exists('%s/rsync.log' %(outdir)):
		os.remove('%s/rsync.log' %(outdir))
	if os.path.exists('%s/s3tmp.log'%(outdir)):
		os.remove('%s/s3tmp.log'%(outdir))
	if os.path.exists('run_aws.job'):
		os.remove('run_aws.job')

#==============================
def relion_autopick_mpi(project):

	#`which relion_autopick` --i CtfFind/job038/micrographs_ctf.star --ref Select/job059/class_averages.star --odir AutoPick/job070/ --pickname autopick --ang 5 --shrink 0 --lowpass 20 --write_fom_maps  --threshold 1 --min_distance 100 --max_stddev_noise 1.5
	#echo CtfFind/job038/micrographs_ctf.star > AutoPick/job070/coords_suffix_autopick.star
	relioncmd,micstar,outdir,refs,killProcess=getCMDautopick(infile)

        if len(killProcess) > 0:
		writeToLog('Error: Detected %s option specified. Please set this option to NO and resubmit' %(killProcess),'%s/run.err' %(outdir))
		sys.exit()

	#Parse relion command to only include input options, removing any mention of 'gpu' or tick marks
        relioncmd=parseCMDautopick(relioncmd)

        #Get AWS region from aws_init.sh environment variable
        awsregion=subprocess.Popen('echo $AWS_DEFAULT_REGION', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsregion) == 0:
                writeToLog('Error: Could not find default region specified as $AWS_DEFAULT_REGION. Please set this environmental variable and try again.','%s/run.err' %(outdir))
                sys.exit()

        #Get AWS ID
        AWS_ID=subprocess.Popen('echo $AWS_ACCOUNT_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        key_ID=subprocess.Popen('echo $AWS_ACCESS_KEY_ID',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        secret_ID=subprocess.Popen('echo $AWS_SECRET_ACCESS_KEY',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        teamname=subprocess.Popen('echo $RESEARCH_GROUP_NAME',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	keypair=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

        #Get AWS CLI directory location
        awsdir=subprocess.Popen('echo $AWS_CLI_DIR', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if len(awsdir) == 0:
                print 'Error: Could not find AWS scripts directory specified as $AWS_CLI_DIR. Please set this environmental variable and try again.'
                sys.exit()

        writeToLog('Starting relion job in the cloud...','%s/run.out' %(outdir))

	ebs_exist=False
        s3_exist=False
        bucketname=''
        otherbucketDirName=''
        if os.path.exists('.aws_relion'):
                for line in open('.aws_relion','r'):
			if line.split()[0].strip().replace('//','/') == micstar.strip().replace('//','/'):
                                bucketname=line.split()[1]
                                #Check if it exists:
                                if os.path.exists('%s/s3out.log' %(outdir)):
                                        os.remove('%s/s3out.log' %(outdir))
                                cmd='aws s3 ls %s > %s/s3out.log' %(bucketname.split('s3://')[-1],outdir)
				subprocess.Popen(cmd,shell=True).wait()
                                if len(open('%s/s3out.log' %(outdir),'r').readlines()) > 0:
                                        s3_exist=True
	keyname=keypair.split('/')[-1].split('.pem')[0]
        keyname=keyname.split('_')
        keyname='-'.join(keyname)
        outdirname=outdir.split('/')
        if len(outdirname[-1]) == 0:
                del outdirname[-1]
        outdirname='-'.join(outdirname)
        outdirname=outdirname.lower().strip()
        keyname=keyname.lower().strip()
        project=project.strip()
        #Upload data to S3
        if s3_exist is False:
                writeToLog('Started micrograph upload on %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
                if len(project) == 0:
			bucketname='rln-aws-tmp-%s/%s/%0.f' %(teamname,keyname,time.time())	
                if len(project) > 0:
                        bucketname='rln-aws-%s-%s/%s/%s' %(teamname,keyname,project,outdirname)
                if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Linux':
                        numCPUs=int(subprocess.Popen('grep -c ^processor /proc/cpuinfo',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                if subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() == 'Darwin':
                        numCPUs=int(subprocess.Popen('sysctl -n hw.ncpu',shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                        numCPUs=1
                bucketname,micdir,otherbucket,otherbucketDirName=rclone_to_s3_mics(micstar,numCPUs*2.4,awsregion,key_ID,secret_ID,bucketname,bucketname,awsdir,project)
                writeToLog('Finished at %s' %(time.asctime(time.localtime(time.time()))),'%s/run.out' %(outdir))
	if s3_exist is True: 
		directoryToTransfer=micstar.split('/')
	        del directoryToTransfer[-1]
        	directoryToTransfer='/'.join(directoryToTransfer)

		#Get column number first
	        o1=open(micstar,'r')
        	for line in o1:
                	if len(line.split())> 0:
                        	if line.split()[0]=='_rlnMicrographName':
                                	micolnum=line.split()[1].split('#')[-1]
	        o1.close()
        	o1=open(micstar,'r')
	        flag=0
        	for line in o1:
                	if len(line.split())> 0:
                        	if os.path.exists(line.split()[int(micolnum)-1]):
                                	if flag == 0:
                                        	path=line.split()[int(micolnum)-1].split('/')
                                        	del path[-1]
                                        	path='/'.join(path)
                                        	flag=1
        	o1.close()
		otherbucket=''
	        if path != directoryToTransfer:
                	otherbucket=bucketname
			
		micdir=directoryToTransfer
		otherbucketDirName=path

        #Get number of movies
        m1=open(micstar,'r')
        movieCounter=0
        for line in m1:
                movieCounter=movieCounter+1
        m1.close()
        movieCounter=movieCounter-3
        if movieCounter > 700:
                instance='p2.8xlarge'
                mpi=32
                gpu=8
                cost=7.2
                numInstancesRequired=1
        if movieCounter <= 700:
                instance='p2.xlarge'
                numInstancesRequired=1
                mpi=4
                gpu=1
                cost=0.9

        writeToLog('Booting up %i x %s virtual machines on AWS to auto pick particles (GPU accelerated) in availability zone %sa' %(numInstancesRequired,instance,awsregion), '%s/run.out' %(outdir))

        instanceNum=0
        ebsVolList=[]
        instanceList=[]
        writeToLog('Creating data storage drive(s) ...','%s/run.out' %(outdir))

	#Get individual file size, multiply by all for downloading all movies
	#if len(otherbucketDirName) == 0:
	dircheck=bucketname.split('s3://')[-1]+'/'
	dircheck=dircheck.replace('//','/')
	tmp=subprocess.Popen('aws s3 ls %s > tmp.log' %(dircheck),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	numfiles=0
	for num in open('tmp.log','r'):
		if 'movie' in num: 
			continue
		if '.mrc' in num: 
			numfiles=numfiles+1
			sizeFile=float(num.split()[-2])
	sizeneeded=math.ceil(sizeFile/1000000000)*2*numfiles
	if sizeneeded <3:
        	sizeneeded=5
        #if len(otherbucketDirName) > 0:
	#	dircheck=bucketname.split('s3://')[-1]+'/'
        #        dircheck=dircheck.replace('//','/')
	#	tmp=subprocess.Popen('aws s3 ls %s-mic/ > tmp.log' %(dircheck),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        #        numfiles=len(open('tmp.log','r').readlines())
        #        sizeFile=float(linecache.getline('tmp.log',3).split()[-2])
        #        sizeneeded=math.ceil(sizeFile//1000000000)*5*numfiles
        #        if sizeneeded <3:
        #                sizeneeded=5
	os.remove('tmp.log')
        while instanceNum < numInstancesRequired:
                #Create EBS volume
                if os.path.exists('%s/awsebs_%i.log' %(outdir,instanceNum)) :
                        os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
                cmd='%s/create_volume.py %i %sa "rln-aws-tmp-%s-%s"'%(awsdir,int(sizeneeded),awsregion,teamname,micstar)+'> %s/awsebs_%i.log' %(outdir,instanceNum)
                subprocess.Popen(cmd,shell=True).wait()
                #Get volID from logfile
                volID=linecache.getline('%s/awsebs_%i.log' %(outdir,instanceNum),5).split('ID: ')[-1].split()[0]
                time.sleep(10)
                os.remove('%s/awsebs_%i.log' %(outdir,instanceNum))
                ebsVolList.append(volID)
                instanceNum=instanceNum+1

        instanceNum=0
        writeToLog('Launching virtual machine ... usually requires 2 - 5 minutes for initialization','%s/run.out' %(outdir))
        while instanceNum < numInstancesRequired:
                #Launch instance
                if os.path.exists('%s/awslog_%i.log' %(outdir,instanceNum)):
                        os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                cmd='%s/launch_AWS_instance.py --relion2 --instance=%s --availZone=%sa --volume=%s > %s/awslog_%i.log' %(awsdir,instance,awsregion,ebsVolList[instanceNum],outdir,instanceNum)
                subprocess.Popen(cmd,shell=True)
                instanceNum=instanceNum+1
                time.sleep(10)
        instanceNum=0
        IPlist=[]
        instanceIDlist=[]
        while instanceNum < numInstancesRequired:
                isdone=0
                qfile='%s/awslog_%i.log'%(outdir,instanceNum)
                while isdone == 0:
                        r1=open(qfile,'r')
                        for line in r1:
                                if len(line.split()) == 2:
                                        if line.split()[0] == 'ID:':
                                                instanceList.append(line.split()[1])
                                                isdone=1
                        r1.close()
                        time.sleep(10)
                instanceID=subprocess.Popen('cat %s/awslog_%i.log | grep ID' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('ID:')[-1]
        	keypair=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split()[3].strip()
	        userIP=subprocess.Popen('cat %s/awslog_%i.log | grep ssh' %(outdir,instanceNum), shell=True, stdout=subprocess.PIPE).stdout.read().split('@')[-1].strip()

                os.remove('%s/awslog_%i.log' %(outdir,instanceNum))
                IPlist.append(userIP)
                instanceIDlist.append(instanceID.strip())
                instanceNum=instanceNum+1

        now=datetime.datetime.now()
	startday=now.day
        starthr=now.hour
        startmin=now.minute

        instanceNum=0
        env.key_filename = '%s' %(keypair)

        writeToLog('Submitting job to the cloud...','%s/run.out' %(outdir))

        #Write .rclone.conf
        homedir=subprocess.Popen('echo $HOME', shell=True, stdout=subprocess.PIPE).stdout.read().split()[0]
        if os.path.exists('%s/.rclone.conf' %(homedir)):
                os.remove('%s/.rclone.conf' %(homedir))

        r1=open('%s/.rclone.conf' %(homedir),'w')
        r1.write('[rclonename]\n')
        r1.write('type = s3\n')
        r1.write('env_auth = false\n')
        r1.write('access_key_id = %s\n' %(key_ID))
        r1.write('secret_access_key = %s\n' %(secret_ID))
        r1.write('region = %s\n' %(awsregion))
        r1.write('endpoint = \n')
        r1.write('location_constraint = %s\n' %(awsregion))
        r1.write('acl = authenticated-read\n')
        r1.write('server_side_encryption = \n')
        r1.write('storage_class = STANDARD\n')
        r1.close()

        while instanceNum < numInstancesRequired:
                env.host_string='ubuntu@%s' %(IPlist[instanceNum])
                othername=''
                if len(otherbucketDirName) > 0:
                        counter=0
                        dirlocation='/data'
                        otherfactor=len(otherbucketDirName.split('/'))
                        if otherfactor == 1:
                                otherfactor=0
                        if otherfactor > 1:
                                otherfactor=1
                        while counter < len(otherbucketDirName.split('/'))-otherfactor:
                                entry=otherbucketDirName.split('/')[counter]
                                exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                                dirlocation=dirlocation+'/'+entry
                                counter=counter+1
                        othername=dirlocation
		#Get micrograph relative path
		micpath=''
		o55=open(micstar,'r')
		for l in o55:
			if len(l.split()) > 0:
				if l.split()[0] == '_rlnMicrographName':
					miccol=int(l.split()[1].split('#')[-1])
		o55.close()
		miccounter=0
		o55=open(micstar,'r')
                for l in o55:
                        if len(l.split()) > 0:
                		if os.path.exists(l.split()[miccol-1]):
					if len(l.split()[miccol-1].split('/')) > 1:
						micpath=l.split()[miccol-1].split('/')
						del micpath[-1]
						micpath='/'.join(micpath)
						miccounter=miccounter+1
		o55.close()

		dirlocation='/data'
                counter=0
                while counter < len(micpath.split('/'))-1:
                        entry=micpath.split('/')[counter]
			exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
                        counter=counter+1

                #Create directories on AWS
                dirlocation='/data'
                counter=0
                while counter < len(micstar.split('/'))-1:
                        entry=micstar.split('/')[counter]
                        exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
                        counter=counter+1
                indirlocation=dirlocation
                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,micstar,IPlist[instanceNum],dirlocation,outdir)
                subprocess.Popen(cmd,shell=True).wait()

		if len(refs) > 0:
			dirlocation='/data'
	                counter=0
                	while counter < len(refs.split('/'))-1:
        	                entry=refs.split('/')[counter]
	                        exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        	dirlocation=dirlocation+'/'+entry
                	        counter=counter+1
        	        reflocation=dirlocation
			localref=refs.split('/')
			del localref[-1]
			localref='/'.join(localref)
			cmd='rsync -avzur -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/*  ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,localref,IPlist[instanceNum],reflocation,outdir)
			subprocess.Popen(cmd,shell=True).wait()

                #Make output directories
		dirlocation='/data'
                counter=0
                while counter < len(outdir.split('/'))-1:
                        entry=outdir.split('/')[counter]
                        exec_remote_cmd('mkdir /%s/%s' %(dirlocation,entry))
                        dirlocation=dirlocation+'/'+entry
                        counter=counter+1

                cmd='rsync -avzur -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/*  ubuntu@%s:/%s/ > %s/rsync.log' %(keypair,outdir,IPlist[instanceNum],dirlocation,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s/rclone ubuntu@%s:~/'%(keypair,awsdir,IPlist[instanceNum])
                subprocess.Popen(cmd,shell=True).wait()

                cmd='scp -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s ~/.rclone.conf ubuntu@%s:~/'%(keypair,IPlist[instanceNum])
                subprocess.Popen(cmd,shell=True).wait()

                micdirlocation=indirlocation
                cloudpath='/data/'+outdir
		exec_remote_cmd('~/rclone sync rclonename:%s /data/%s --quiet --max-size 1G --transfers %i' %(bucketname.split('s3://')[-1],micpath,mpi*3))
                if len(otherbucketDirName) > 0:
			exec_remote_cmd('~/rclone sync rclonename:%s %s --quiet --transfers %i' %(bucketname.split('s3://')[-1],micpath,mpi*3))
			
                if gpu  == 1:
                        relion_remote_cmd='/home/EM_Packages/relion2.0/build/bin/relion_autopick %s --gpu ' %(relioncmd)
                if gpu > 1:
                        relion_remote_cmd='mpirun -np %i /home/EM_Packages/relion2.0/build/bin/relion_autopick_mpi %s --gpu ' %(gpu,relioncmd)
                o2=open('run_aws.job','w')
                o2.write('#!/bin/bash\n')
                o2.write('cd /data\n')
                o2.write('%s\n' %(relion_remote_cmd))
                o2.close()
                st = os.stat('run_aws.job')
                os.chmod('run_aws.job', st.st_mode | stat.S_IEXEC)
                cmd='rsync -avzu -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" run_aws.job ubuntu@%s:~/ > %s/rsync.log' %(keypair,IPlist[instanceNum],outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -n -f -i %s ubuntu@%s "export LD_LIBRARY_PATH=/home/EM_Packages/relion2.0/build/lib::/usr/local/cuda/lib64:$LD_LIBRARY_PATH && nohup ./run_aws.job > /data/%s/run.out 2> /data/%s/run.err < /dev/null &"' %(keypair,IPlist[instanceNum],outdir,outdir)
		subprocess.Popen(cmd,shell=True)
		instanceNum=instanceNum+1
		
        cmd='rsync --ignore-errors  -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" %s/run.out ubuntu@%s:/data/%s/ > %s/rsync.log' %(keypair,outdir,IPlist[0],outdir,outdir)
        subprocess.Popen(cmd,shell=True).wait()
	isdone=0
	while isdone ==0: 
        	#Check if job was specified to be killed
                isdone=check_and_kill_job('%s/note.txt' %(outdir),IPlist[0],keypair)

		cmd='rsync -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(keypair,IPlist[0],outdir,outdir,outdir)
		subprocess.Popen(cmd,shell=True).wait()

		if os.path.exists('%s/Micrographs/' %(outdir)): 
			if len(glob.glob('%s/Micrographs/*' %(outdir))) > 0:
				numdone=float(subprocess.Popen('ls %s/Micrographs/* | wc -l' %(outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip())
				if numdone == float(numfiles):
					isdone=1
		
		#Check if there are any errors
                if isdone == 0:
                	if os.path.exists('%s/run.err' %(outdir)):
                        	if float(subprocess.Popen('cat %s/run.err | wc -l' %(outdir),shell=True, stdout=subprocess.PIPE).stdout.read().strip()) > 0:
                                	writeToLog('\nError detected in run.err. Shutting down instance.','%s/run.out' %(outdir))
                                        isdone=1
        time.sleep(15)

        writeToLog('Job finished!','%s/run.out' %(outdir))

	cmd='rsync --no-links -avzuq -e "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s" ubuntu@%s:/data/%s/ %s/ > %s/rsync.log' %(keypair,IPlist[0],outdir,outdir,outdir)
        subprocess.Popen(cmd,shell=True).wait()

        for instanceID in instanceIDlist:
                #Kill all instances
		cmd='aws ec2 terminate-instances --instance-ids %s > %s/tmp4949585940.txt' %(instanceID,outdir)
                subprocess.Popen(cmd,shell=True).wait()
	
        for instanceID in instanceIDlist:
                isdone=0
                while isdone == 0:
                        status=subprocess.Popen('aws ec2 describe-instances --instance-ids %s --query "Reservations[*].Instances[*].{State:State}" | grep Name'%(instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split()[-1].split('"')[1]
                        if status == 'terminated':
                                isdone=1
                        time.sleep(10)

        for volID in ebsVolList:
                cmd='%s/kill_volume.py %s > %s/awslog.log' %(awsdir,volID,outdir)
                subprocess.Popen(cmd,shell=True).wait()

        now=datetime.datetime.now()
        finday=now.day
        finhr=now.hour
        finmin=now.minute
        if finday != startday:
                finhr=finhr+24
        deltaHr=finhr-starthr
        if finmin > startmin:
                deltaHr=deltaHr+1
        if not os.path.exists('aws_relion_costs.txt'):
                cmd="echo 'Input                   Output               Cost ($)' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
                cmd="echo '-----------------------------------------------------------' >> aws_relion_costs.txt"
                subprocess.Popen(cmd,shell=True).wait()
        cmd='echo "%s      %s      %.02f  " >> aws_relion_costs.txt' %(micstar,outdir,float(deltaHr)*float(cost)*numInstancesRequired)
        subprocess.Popen(cmd,shell=True).wait()

	#Write single output file
	#echo CtfFind/job038/micrographs_ctf.star > AutoPick/job088/coords_suffix_autopick.sta
	cmd='echo %s > %s/coords_suffix_autopick.star' %(micstar,outdir)
	subprocess.Popen(cmd,shell=True).wait()

        #Update .aws_relion
        if os.path.exists('.aws_relion_tmp'):
                os.remove('.aws_relion_tmp')
        if os.path.exists('.aws_relion'):
                shutil.move('.aws_relion','.aws_relion_tmp')
                tmpout=open('.aws_relion','w')
                for line in open('.aws_relion_tmp','r'):
                        tmpout.write(line)
                tmpout.close()
                os.remove('.aws_relion_tmp')
        cmd='echo "%s     %s      ---" >> .aws_relion' %(outdir,bucketname)
        subprocess.Popen(cmd,shell=True).wait()
        
	if len(project) > 0:
                projectbucket='rln-aws-%s-%s/%s' %(teamname,keyname,project)

                cmd='aws s3 cp .aws_relion s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                if os.path.exists('.aws_relion_project_info'):
                        cmd='aws s3 cp .aws_relion_project_info s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp aws_relion_costs.txt s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                #Remove all micrographs in bucket already
                #cmd='aws s3 rm s3://%s/%s/ --recursive > s3tmp.log' %(projectbucket,outdirname)
                #subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 sync %s/ s3://%s/%s > %s/s3tmp.log ' %(outdir,projectbucket,outdirname,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                cmd='aws s3 cp default_pipeline.star s3://%s/ > %s/s3tmp.log' %(projectbucket,outdir)
                subprocess.Popen(cmd,shell=True).wait()

                guilist=glob.glob('.gui*')
                for gui in guilist:
                        cmd='aws s3 cp %s s3://%s/ > %s/s3tmp.log' %(gui,projectbucket,outdir)
                        subprocess.Popen(cmd,shell=True).wait()
                if os.path.exists('%s/s3tmp.log'%(outdir)):
                        os.remove('%s/s3tmp.log'%(outdir))	

	if os.path.exists('%s/rsync.log'%(outdir)):
                os.remove('%s/rsync.log'%(outdir))
        moviestarlist=glob.glob('movies*.star')
        for moviestar in moviestarlist:
                if os.path.exists(moviestar):
                        os.remove(moviestar)
        if os.path.exists('run_aws.job'):
                os.remove('run_aws.job')

#==============================
if __name__ == "__main__":

	#Read relion command from appion
	in_cmd=sys.argv[1]

	sys.exit()

	jobtype,numjobsIn=getJobType(infile)
	
	if jobtype == 'None':
		print 'Error: unrecognized relion command'
		sys.exit()
	project=''
	#Get project name if exists
	if os.path.exists('.aws_relion_project_info'):
		project=linecache.getline('.aws_relion_project_info',1).split('=')[-1]

	#Align movies
	if jobtype  == 'relion_run_motioncorr' or jobtype == 'relion_run_motioncorr_mpi':
		relion_run_motioncorr(project)

	#CTF estimation
	if jobtype  == 'relion_run_ctffind' or jobtype == 'relion_run_ctffind_mpi':
                relion_run_ctffind(project)

	#Extract particles
	if numjobsIn == 1:
		if jobtype == 'relion_preprocess' or jobtype == 'relion_preprocess_mpi':
        	        relion_preprocess_mpi(project)

	#Perform 2D or 3D classification / refinement
	if jobtype == 'relion_refine' or jobtype == 'relion_refine_mpi':
		relion_refine_mpi(project)

	#Submit auto picking job to GPUs
	if jobtype == 'relion_autopick' or jobtype == 'relion_autopick_mpi':
		relion_autopick_mpi(project)

	#Movie refinemnt
	if numjobsIn==2:
		relion_movie_refine(project)

	print 'Error: Job submission not recognized. Exiting'
