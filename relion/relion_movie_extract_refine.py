#!/usr/bin/env python
import shutil 
import time
import linecache
import sys
import os
import subprocess

micstar=sys.argv[1]
micBucketName=sys.argv[2]
micDir=sys.argv[3]
numThreads=float(sys.argv[4])
extractBucket=sys.argv[5]
extractDest=sys.argv[6]
relioncmd=sys.argv[7]
outdir=sys.argv[8]
number=int(sys.argv[9])

if numThreads==4: 
	numToGet=4
	numFilesAtATime=4	
	numMPI=4
if numThreads==10:
        numToGet=4
        numFilesAtATime=4	
	numMPI=4
if numThreads == 16: 
	numToGet=16
	numFilesAtATime=16
if numThreads == 36:
        numToGet=36
        numFilesAtATime=36
if numThreads == 87:
        numToGet=36
        numFilesAtATime=36
	numMPI=36
relionpath='/home/EM_Packages/relion2.0/build/bin/relion_run_motioncorr'
relionhandler='/home/EM_Packages/relion2.0/build/bin/relion_image_handler'

#===================
def parseCMD(rlncmd):
	#Example cmd: --i s3-empiar-10061/motioncorr-job007/ --o MotionCorr/job051/ --first_frame_sum 1 --last_frame_sum 0 --bin_factor 1 --motioncorr_exe  --bfactor 150 --gpu 0
	counter=0
	patchxnum=0
	patchynum=0
	kevnum=0
	dosenum=0
	prenum=0	
	apixnum=0
	patchx=''
	patchy=''
	kev=''
	dose=''
	preexp=''
	apix=''
	for rln in rlncmd.split(): 
		if rln=='--angpix':
			apixnum=counter+1
		if rln=='--patch_x': 
			patchxnum=counter+1
		if rln=='--patch_y':
                        patchynum=counter+1		
		if rln=='--voltage': 
			kevnum=counter+1
		if rln=='--dose_per_frame':
			dosenum=counter+1
		if rln=='--preexposure':
			prenum=counter+1
		if rln=='--o': 
			outnum=counter+1
		if rln == '--first_frame_sum': 
			firstnum=counter+1
		if rln == '--last_frame_sum': 
			lastnum=counter+1
		if rln == '--bin_factor': 
			binnum=counter+1
		if rln == '--bfactor': 
			bnum=counter+1	
		counter=counter+1
	if apixnum > 0: 
		apix=rlncmd.split()[apixnum]
	if patchxnum > 0:
		patchx=rlncmd.split()[patchxnum]
	if patchynum > 0: 
		patchy=rlncmd.split()[patchynum]
	if kevnum > 0: 
		kev=rlncmd.split()[kevnum]
	if dosenum > 0: 
		dose=rlncmd.split()[dosenum]
	if prenum > 0: 
		preexp=rlncmd.split()[prenum]
	return rlncmd.split()[outnum],rlncmd.split()[bnum],rlncmd.split()[firstnum],rlncmd.split()[lastnum],rlncmd.split()[binnum],patchx,patchy,kev,dose,preexp,apix

#Num header lines in micstar
numheader=1
destdir=''
micflag=0
movielist=[]
o1=open(micstar,'r')
for line in o1: 
	if len(line.split('.mrc')) == 1: 
		numheader=1+numheader
	if len(line.split('.mrc')) > 1:
		if micflag == 0:
			if len(line.split('/')) > 1: 
				for folder in line.split('/'): 
					if len(folder.split('.mrc')) == 1: 
						if len(destdir) > 0:
                                                        destdir=destdir+'/'+folder
						if len(destdir) == 0: 
							destdir=folder+'/'
			micflag=1
		movielist.append(line)
o1.close()
#Get mics
counter=0
if numToGet > len(movielist): 
	numToGet==len(movielist)

miclist=[]
if os.path.exists('rcloneMicList.txt'): 
	os.remove('rcloneMicList.txt')
r1=open('rcloneMicList.txt','w')
#while counter < int(numFilesAtATime): 
while counter < len(movielist):
	#Get mic and copy into correct location
	localmicpath=linecache.getline(micstar,counter+numheader).strip()
	if len(localmicpath.split('/')) == 1: 
		micname=localmicpath
	if len(localmicpath.split('/')) > 1: 
		micname=localmicpath.split('/')[-1]
	miclist.append(localmicpath)
	#Write files into rclone input list
	r1.write('%s\n' %(micname))
	counter=counter+1
r1.close()

#Rclone movies to destindation directory 
cmd='~/rclone sync rclonename:%s %s/ --include-from rcloneMicList.txt --transfers %i' %(micBucketName,destdir,int(numFilesAtATime))
print cmd
subprocess.Popen(cmd,shell=True).wait()
os.remove('rcloneMicList.txt')

#Rclone extract directory
cmd='~/rclone sync rclonename:%s %s --transfers %i' %(extractBucket,extractDest,int(numFilesAtATime))
print cmd 
subprocess.Popen(cmd,shell=True).wait()

cmd='mpirun -np %i relion_preprocess_mpi %s --i %s' %(numMPI,relioncmd,micstar)
print cmd
subprocess.Popen(cmd,shell=True).wait()

#out_upload_bucket
outBucket=extractBucket.split('/')
del outBucket[-1]
outBucket='/'.join(outBucket)+'/'+outdir.split('/')[0].lower()+'-'+outdir.split('/')[1]

#Rename output files
shutil.move('%s/micrographs_movie_list.star' %(outdir),'%s/micrographs_movie_list_%i.star' %(outdir,number))
if os.path.exists('%s/batch_50mics_nr001.star' %(outdir)): 
	shutil.move('%s/batch_50mics_nr001.star' %(outdir),'%s/batch_50mics_nr001_%i.star' %(outdir,number))
if os.path.exists('%s/particles_movie.star' %(outdir)): 
	shutil.move('%s/particles_movie.star' %(outdir),'%s/particles_movie_%i.star' %(outdir,number))

cmd='~/rclone copy %s/ rclonename:%s --transfers %i --exclude=particles_movie_%i.star' %(outdir,outBucket,int(numFilesAtATime),number)
print cmd
subprocess.Popen(cmd,shell=True).wait()

cmd='~/rclone copy %s/particles_movie_%i.star rclonename:%s' %(outdir,number,outBucket)
print cmd
subprocess.Popen(cmd,shell=True).wait()
