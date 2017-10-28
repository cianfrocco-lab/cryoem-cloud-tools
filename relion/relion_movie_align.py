#!/usr/bin/env python
import time
import linecache
import sys
import os
import subprocess

micstar=sys.argv[1]
numThreads=int(sys.argv[2])
micBucketName=sys.argv[3]
movieBucket=sys.argv[4]
numFilesAtATime=int(sys.argv[5])
aligntype=sys.argv[6] #unblur vs. motioncorr vs. motioncor2
relioncmd=sys.argv[7]
gainref=sys.argv[8]
outdir=sys.argv[9]
angpix=float(sys.argv[10])
savemovies=sys.argv[11]
if numThreads==1:
	numToGet=1
	numFilesAtATime=1
	group1_s=0
	group1_f=1
	group2_s=2
        group2_f=3
if numThreads==2:
        numThreads=1
	numToGet=1
        numFilesAtATime=1
        group1_s=0
        group1_f=1
        group2_s=2
        group2_f=3
if numThreads==8: 
	numToGet=8
	numFilesAtATime=8
	group1_s=8
	group1_f=19
	group2_s=20
	group2_f=31
if numThreads == 16: 
	if aligntype != 'unblur':
		numToGet=16
		numFilesAtATime=16
        	group1_s=16
	        group1_f=38
	        group2_s=39
	        group2_f=63

	if aligntype == 'unblur':
		numThreads=9
                numToGet=9
                numFilesAtATime=9
                group1_s=9
                group1_f=18
                group2_s=27
                group2_f=31
if numThreads == 64: 
	numThreads=32
        numToGet=32
        numFilesAtATime=10
        group1_s=40
        group1_f=95
        group2_s=96
        group2_f=128
motioncor2path='/home/EM_Packages/MotionCor2/MotionCor2-08-22-2016'
motioncorrpath='/home/EM_Packages/motioncorr_v2.1/bin/dosefgpu_driftcorr'
#unblurpath='/home/EM_Packages/unblur_1.0.2/bin/unblur_openmp_7_17_15.exe'
summoviepath='/home/EM_Packages/summovie_1.0.2/bin/sum_movie_openmp_7_17_15.exe'
relionpath='/home/EM_Packages/relion2.0/build/bin/relion_run_motioncorr'
relionhandler='/home/EM_Packages/relion2.0/build/bin/relion_image_handler'

#download unblur
cmd='wget http://grigoriefflab.janelia.org/sites/default/files/unblur_1.0.2.tar.gz'
subprocess.Popen(cmd,shell=True).wait()

cmd='tar xvzf unblur_1.0.2.tar.gz'
subprocess.Popen(cmd,shell=True).wait()

unblurpath='/data/unblur_1.0.2/bin/unblur_openmp_7_17_15.exe'

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
	bnum=0
	binnum=0
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

#===================
def checkLog(newcheck,aligntype): 
	
	finished='nope'
	restart='no'

	if aligntype == 'motioncorr':
		print 'checking'
		print '%s.log' %(newcheck.split('.%s' %(newcheck.split('.')[-1]))[0]) #newcheck[:-4])
		if os.path.exists('%s.log' %(newcheck.split('.%s' %(newcheck.split('.')[-1]))[0])): 
			o44=open('%s.log' %(newcheck.split('.%s' %(newcheck.split('.')[-1]))[0]),'r')
			for line in o44: 
				if len(line.split()) > 0: 
					if line.split()[0] == 'Done.': 
						finished='done'
					if line.split()[0] == 'Failed': 
						finished='nope'
						restart='yes'
			o44.close()
	if aligntype == 'motioncor2':
	  	print 'checking'
		status=subprocess.Popen('cat %s.out | grep Computational' %(newcheck.split('.%s' %(newcheck.split('.')[-1]))[0]),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		if len(status) > 0: 
			finished='done'
	return finished,restart

#=====================
def uploadRsync(dirToSync,outbucket,rclonetxt,filesAtATime,f1,f2,f3,f4,taskstart,taskfin): 
	
	outfile='rcloneupload_%0.i.txt' %(time.time())
	if os.path.exists(outfile): 
		time.sleep(2)
	outfile='rcloneupload_%0.i.txt' %(time.time())

	o33=open(outfile,'w')
	o33.write('#!/bin/bash\n')
	o33.write('sleep 1m\n')
	o33.write('taskset -c %i-%i ~/rclone sync %s %s --retries 10 --quiet --include-from %s --transfers %i > %s_rclone.txt\n' %(taskstart,taskfin,dirToSync,outbucket,rclonetxt,1,outfile[:-4]))
	print 'taskset -c %i-%i ~/rclone sync %s %s --quiet --include-from %s --transfers %i > rclonetmp1.txt\n' %(taskstart,taskfin,dirToSync,outbucket,rclonetxt,1)
	#o33.write('taskset -c %i-%i ~/rclone sync %s %s --quiet --include-from %s --transfers %i > rclonetmp1.txt\n' %(group1_s,group1_f,dirToSync,outbucket,rclonetxt,filesAtATime))
	o33.write('/bin/rm %s\n' %(f1))  #newcheck))
	o33.write('/bin/rm %s\n' %(f2)) #newcheck, '%s/%s' %(destdir,check.split('/')[-1]),'%s_movie.mrcs' %(newcheck[:-4]),'%s_bin.mrc' %(newcheck[:-4])
	if os.path.exists(f3): 
		o33.write('/bin/rm %s\n' %(f3)) 
	if os.path.exists(f4): 
		o33.write('/bin/rm %s\n' %(f4))
	if os.path.exists("%s_DW.mrc" %(f4[:-4])): 
		o33.write('/bin/rm %s_DW.mrc\n' %(f4[:-4]))
	o33.write('/bin/rm %s\n' %(rclonetxt))
	o33.close()
	cmd='/bin/chmod +x %s' %(outfile)
        subprocess.Popen(cmd,shell=True).wait()
	cmd='./%s' %(outfile)
        subprocess.Popen(cmd,shell=True)
	
def writeRunUnBlurSum(relioncmd,micname,additionalcmds,totframes,task1): 
	#--o MotionCorr/job082/ --first_frame_sum 1 --last_frame_sum 0 --use_unblur --j 1  --angpix 0.6 --dose_weighting --voltage 200 --dose_per_frame 1.3 --preexposure 0
	tot=len(relioncmd.split())
	counter=0
	doseweight=False
	savemovies=False
	while counter < tot: 
		entry=relioncmd.split()[counter]
		if entry == '--o': 
			outdir=relioncmd.split()[counter+1]
		if entry == '--first_frame_sum': 
			firstframe=relioncmd.split()[counter+1]
		if entry == '--last_frame_sum': 
			lastframesum=int(relioncmd.split()[counter+1])
		if entry == '--angpix': 
			apix=relioncmd.split()[counter+1]
		if entry == '--dose_weighting': 
			doseweight=True
		if entry == '--dose_per_frame': 
			doseperframe=relioncmd.split()[counter+1]
		if entry == '--voltage': 
			voltage=relioncmd.split()[counter+1]
		if entry == '--preexposure': 
			prexpose=relioncmd.split()[counter+1]
		if entry == '--save_movies': 
			savemovies=True
		counter=counter+1
	if float(lastframesum) == 0: 
		lastframesum = totframes
	outmicname='%s/%s' %(outdir,micname)
	scriptrun='%s_unblur.com' %(outmicname[:-(len(outmicname.split('.')[-1])+1)])
	unblurlog='%s_unblur.log' %(outmicname[:-(len(outmicname.split('.')[-1])+1)])
	sumlog='%s_sum.log' %(outmicname[:-(len(outmicname.split('.')[-1])+1)])
	shifts='%s_shifts.txt' %(outmicname[:-(len(outmicname.split('.')[-1])+1)])

	finddirs=outmicname.split('/')
	curr=''
	for find in finddirs: 
		if len(find) == 0: 
			continue
		if len(curr) > 0: 
			curr=curr+'/'+find+'/'
		if len(curr) == 0:
                        curr=find+'/'
		if os.path.isdir(curr) is False: 
			if len(curr.split('.mrc')) == 1:
				if curr != micname.split('/')[-1]: 
					os.makedirs(curr)
	if os.path.exists(scriptrun): 
		os.remove(scriptrun)
	o1=open(scriptrun,'w')
	o1.write('#!/bin/bash\n')
	o1.write('export  OMP_NUM_THREADS=1\n')
	o1.write('mkdir %s\n' %(outmicname.split('.')[0]))
	o1.write('cd %s\n' %(outmicname.split('.')[0]))
	o1.write('%s > /data/%s << EOF\n' %(unblurpath,unblurlog))
	o1.write('/data/%s\n' %(micname)) #micname.split(micname.split('/')[-1])[0],micname.split('/')[-1]))
	o1.write('%s\n' %(totframes))
 	o1.write('../%s\n' %(outmicname.split('/')[-1]))
	o1.write('../%s\n' %(shifts.split('/')[-1]))
	o1.write('%s\n' %(apix))
	if doseweight is True: 
		o1.write('YES\n')
		o1.write('%s\n' %(doseperframe))
		o1.write('%s\n' %(voltage))
		o1.write('%s\n' %(prexpose))
	if doseweight is False: 
		o1.write('NO\n')
	if savemovies is True: 
		o1.write('YES\n')
		movieout=outmicname.split('.')
		del movieout[-1]
		movieout='.'.join(movieout)
		o1.write('../%s_movie.mrc\n' %(movieout.split('/')[-1]))
	if savemovies is False: 
		o1.write('NO\n')
	o1.write('NO\n')
	o1.write('EOF\n')
	o1.close()
	cmd='/bin/chmod +x %s' %(scriptrun)
	subprocess.Popen(cmd,shell=True).wait()
	cmd='taskset -c %i ./%s' %(task1,scriptrun)
	print cmd
	subprocess.Popen(cmd,shell=True)
	print '--> started running unblur for %s' %(micname)
#Num header lines in micstar
numheader=1
destdir=''
micflag=0
movielist=[]
o1=open(micstar,'r')
for line in o1:	
	#newcheck.split('.%s' %(newcheck.split('.')[-1]))[0] 
	print line.split('.%s' %(line.split('.')[-1]))[0]
	print len(line.split('.%s' %(line.split('.')[-1]))[0])
	if len(line.split('.%s' %(line.split('.')[-1]))[0].split('/')) == 1: 
		print numheader
		numheader=1+numheader
	if len(line.split('.%s' %(line.split('.')[-1]))[0].split('/')) > 1:
		if micflag == 0:
			if len(line.split('/')) > 1: 
				print line.split('/')
				for folder in line.split('/'):
					if folder != line.split('/')[-1]:
						if len(destdir) > 0:
                                                        destdir=destdir+'/'+folder
                                                if len(destdir) == 0: 
                                                        destdir=folder+'/'
					''' 
					if len(folder.split(line.split('.%s' %(line.split('.')[-1]))[0])) == 1: 
						if len(destdir) > 0:
                                                        destdir=destdir+'/'+folder
						if len(destdir) == 0: 
							destdir=folder+'/'
					'''
			micflag=1
		movielist.append(line)
o1.close()
#Get initial round of mics
counter=0

if numToGet > len(movielist): 
	numToGet==len(movielist)
print 'movielist=%s' %movielist
miclist=[]
if len(destdir) > 0: 
	if not os.path.exists(destdir): 
		os.makedirs(destdir)
	if not os.path.exists('%s/%s/' %(outdir,destdir)): 
		os.makedirs('%s/%s/' %(outdir,destdir))
if os.path.exists('rcloneMicList.txt'): 
	os.remove('rcloneMicList.txt')
r1=open('rcloneMicList.txt','w')
#while counter < int(numFilesAtATime): 
while counter < numToGet:
	#Get mic and copy into correct location
	localmicpath=linecache.getline(micstar,counter+numheader).strip()
	if len(localmicpath.split('/')) == 1: 
		micname=localmicpath
	if len(localmicpath.split('/')) > 1: 
		micname=localmicpath.split('/')[-1]
	miclist.append(localmicpath)
	#Write files into rclone input list
	print 'initial file to get %s' %(micname)
	r1.write('%s\n' %(micname))
	counter=counter+1
r1.close()

cmd='touch done_list.txt'
subprocess.Popen(cmd,shell=True).wait()

#Rclone movies to destindation directory
print 'downloading initial mic(s)' 
cmd='~/rclone sync rclonename:%s %s/ --include-from rcloneMicList.txt --transfers %i' %(movieBucket,destdir,int(numFilesAtATime))
print cmd
subprocess.Popen(cmd,shell=True).wait()
os.remove('rcloneMicList.txt')
movieCounter=0
toGetCounter=numToGet-1
while movieCounter < len(movielist): 
	threadnum=0
	outCheckList=[]
	movieDLchecklist=[]
	while threadnum < numThreads: 
		micnum=movieCounter+threadnum
		print micnum 
		if micnum >=len(movielist): 
			threadnum=threadnum+1
		if micnum < len(movielist): 
			#select single line from relion mic star file 
			micname=movielist[micnum].strip()
			print 'working on %s' %(micname)
			additionalcmds=''
			checkexist=0
                        while checkexist == 0:
                                if os.path.exists(micname):
                        		checkexist=1
			if micnum == 0:	
				cmd='/home/EM_Packages/relion2.0/build/bin/relion_image_handler --i %s --stats > handler.txt' %(micname)
				subprocess.Popen(cmd,shell=True).wait()
				outline=linecache.getline('handler.txt',1).split('=')[1].split('x')[2]
				lastframeREAL=subprocess.Popen('relion_image_handler --i %s --stats' %(micname),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split('=')[1].split('x')[2]
			if aligntype == 'unblur': 
				additionlcmds=additionalcmds+' --use_unblur'+' --unblur_exe %s' %(unblurpath)+' --summovie_exe %s' %(summoviepath)+' --j 1'
			if aligntype == 'motioncorr':
				additionalcmds=additionalcmds+' --motioncorr_exe %s' %(motioncorrpath)+' --gpu %i' %(threadnum)
			if aligntype == 'motioncor2': 
				additionalcmds=additionalcmds+' --motioncorr_exe %s' %(motioncor2path)+' --use_motioncor2'+' --gpu %i' %(threadnum)
			if gainref != '-1': 
				additionalcmds=additionalcmds+' --gainref %s' %(gainref)
			
			#/home/EM_Packages/motioncorr_v2.1/bin/dosefgpu_driftcorr Micrographs/EMD-2984_0006_frames.mrc -fcs MotionCorr/job051/Micrographs/EMD-2984_0006_frames.mrc -flg MotionCorr/job051/Micrographs/EMD-2984_0006_frames.log -nst 0 -nss 0 -ned 0 -nes 0 -bft 150 -gpu 6 >> MotionCorr/job051/Micrographs/EMD-2984_0006_frames.out 2>> MotionCorr/job051/Micrographs/EMD-2984_0006_frames.err
			outdir,bfactor,firstframe,lastframe,binfactor,patchx,patchy,kev,dose,preexp,apix=parseCMD(relioncmd)
			if float(lastframe) == 0: 
				lastframe=int(lastframeREAL)
			if aligntype == 'motioncorr': 
				#Parse relion command for info:
				if savemovies == 'False':
					savecmd=''
				if savemovies == 'True':
					savecmd=' -ssc 1 -fct %s/%s_movie.mrcs ' %(outdir,micname.split('.%s' %(micname.split('.')[-1]))[0]) 
				cmd='taskset -c %i %s %s -fcs %s/%s.mrc -flg %s/%s.log -nss %s -nes %s -bft %s -gpu %i %s >> %s/%s.out 2>> %s/%s.err & ' %(threadnum,motioncorrpath,micname,outdir,micname.split('.%s' %(micname.split('.')[-1]))[0],outdir,micname.split('.%s' %(micname.split('.')[-1]))[0],firstframe,lastframe,bfactor,threadnum,savecmd,outdir,micname.split('.%s' %(micname.split('.')[-1]))[0],outdir,micname.split('.%s' %(micname.split('.')[-1]))[0])
				print cmd 
				subprocess.Popen(cmd,shell=True)
			if aligntype == 'motioncor2': 
				#cmd='nohup taskset -c %i %s --i %s' %(threadnum,relionpath,micname)+' '+relioncmd+' '+additionalcmds+' &'
				lastframe=int(lastframe)-1
				if lastframe <0:
					lastframe=0
				doseline='  '
				if len(dose) > 0: 
					doseline=' -FmDose %s -PixSize %s -InitDose %s -kV %s' %(dose,apix,preexp,kev)
				cmd='taskset -c %i %s -InMrc %s -OutMrc %s/%s.mrc -Throw %i -Trunc %i -Bft %s -Iter 10 -Patch %s %s -Gpu %i -FtBin %s %s >> %s/%s.out 2>> %s/%s.err &' %(threadnum,motioncor2path,micname,outdir,micname.split('.%s' %(micname.split('.')[-1]))[0],int(firstframe)-1,lastframe,bfactor,patchx,patchy,threadnum,binfactor,doseline,outdir,micname.split('.%s' %(micname.split('.')[-1]))[0],outdir,micname.split('.%s' %(micname.split('.')[-1]))[0])
				#cmd = '%s -InMrc %s -OutMrc %s -Throw %i -Bft %i -Iter 10 -Patch %i %i -FtBin %i -FmDose %f %s %s' %(motionCor2Path,inmovie,outmicro,params['throw'],params['bfactor'],params['patch'],params['patch'],params['binning'],params['doserate'],doseinfo,gainref)
				print cmd
				subprocess.Popen(cmd,shell=True)
			if aligntype == 'unblur': 
				writeRunUnBlurSum(relioncmd,micname,additionalcmds,lastframe,threadnum)
			newnamesplit=micname.split('.')
			outCheckList.append('%s' %(micname))
	
			if os.path.exists('rcloneMicList_%i.txt' %(threadnum)): 
				os.remove('rcloneMicList_%i.txt' %(threadnum))
			
			nextmicNum=micnum+numThreads+1
			threadnum=threadnum+1
	print 'waiting...'
	#Start transfer of next batch
	if os.path.exists('rcloneMicList1111.txt'):
        	os.remove('rcloneMicList1111.txt')
	toGetCounter=nextmicNum-numThreads
	print 'next mic num %i' %(toGetCounter)
	maxnumnext=toGetCounter+numToGet
	if maxnumnext >=len(movielist): 
		maxnumnext=len(movielist)
	while toGetCounter < maxnumnext: 
		micname=movielist[toGetCounter]
		if len(micname.split('/')) == 1:
                	micnameonly=micname.strip()
                if len(micname.split('/')) > 1:
                        micnameonly=micname.split('/')[-1].strip()
               	cmd='echo "%s" >> rcloneMicList1111.txt' %(micnameonly)
		subprocess.Popen(cmd,shell=True).wait()
		toGetCounter=toGetCounter+1

	time.sleep(10)
	cmd='taskset -c %i-%i ~/rclone sync rclonename:%s %s/ --include-from rcloneMicList1111.txt --transfers %i' %(group1_f,group2_f,movieBucket,destdir,numToGet)
	print cmd 
	subprocess.Popen(cmd,shell=True).wait()

	if os.path.exists('rcloneMicList1111.txt'): 
		os.remove('rcloneMicList1111.txt')
	
	#Start waiting for 1) jobs to finish and 2) movies have been downloaded
	fincounter=0
	for check in outCheckList: 
		isdone=0
		newnamesplit=check.split('.')
                if aligntype != 'unblur': 
			if len(newnamesplit) > 2:
	                	del newnamesplit[-1]
                        	newnamesplit='_'.join(newnamesplit)
                       		newmicname=newnamesplit+'.'+micname.split('.')[-1]
                	if len(newnamesplit) == 2:
                        	newmicname='%s.mrc' %(check.split('.%s' %(check.split('.')[-1]))[0])
                	newcheck=outdir+'/'+newmicname
			newcheck=newcheck.strip()
		if aligntype == 'unblur': 
			newcheck=outdir+'/'+check
		while isdone == 0:
			print 'waiting on %s' %(newcheck)
			if aligntype != 'unblur': 
				micstatus,restart=checkLog(newcheck,aligntype)
				if restart == 'yes': 
					cmd='%s.com&' %(newcheck[:-4])
					print cmd
					subprocess.Popen(cmd,shell=True)
					###FIL> IN HERE
				if micstatus == 'done':
					if os.path.exists(newcheck):
						print '--------------finished %s' %(newcheck)
						isdone=1
						rclonetxt='rcloneMicList_%0.i' %(time.time())
						if os.path.exists(rclonetxt): 
							os.remove(rclonetxt)
						if len(check.split('/')) == 1:
							micname=check
						if len(check.split('/')) > 1:
							micname=check.split('/')[-1]
						if angpix == -1: 
							angpix=1	
					#cmd='%s --i %s --o %s_bin.mrc --angpix %f --rescale_angpix %f' %(relionhandler,newcheck,newcheck[:-4],angpix,angpix*4)
					#subprocess.Popen(cmd,shell=True).wait()

						cmd='echo "%s" >> %s' %(newcheck.split('/')[-1],rclonetxt)
        	                        	subprocess.Popen(cmd,shell=True)

						if len(kev) > 0:
							cmd='echo "%s_DW.mrc" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
							subprocess.Popen(cmd,shell=True)	
					#cmd='echo "%s_bin.mrc" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                	                #subprocess.Popen(cmd,shell=True)

						cmd='echo "%s.out" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
        	                        	subprocess.Popen(cmd,shell=True)

						cmd='echo "%s_shifts.eps" >> %s' %(check.split('/')[-1][:-4],rclonetxt)
                        	               	subprocess.Popen(cmd,shell=True)

						if savemovies == 'True': 
							cmd='echo "%s_movie.mrcs" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
							subprocess.Popen(cmd,shell=True)

						cmd='echo "%s" >> done_list.txt' %(newcheck.split('/')[-1])
						subprocess.Popen(cmd,shell=True)
	
						#cmd='taskset -c 17-21 ~/rclone sync %s/%s %s --include-from %s --transfers %i' %(outdir,destdir,micBucketName,rclonetxt,numToGet)
						#subprocess.Popen(cmd,shell=True)
                        	 	        #print cmd 
						uploadRsync('%s/%s' %(outdir,destdir),'%s'%(micBucketName),rclonetxt,int(numToGet),newcheck, '%s/%s' %(destdir,check.split('/')[-1]),'%s_movie.mrcs' %(newcheck[:-4]),'%s_bin.mrc' %(newcheck[:-4]),group2_s,group2_f)
					
			if aligntype == 'unblur':
				unblurbase=newcheck[:-(len(newcheck.split('.')[-1])+1)]
				if os.path.exists('%s_unblur.log' %(unblurbase)):
					checkdone=subprocess.Popen('/bin/cat %s_unblur.log | /bin/grep cleanly' %(unblurbase),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
					if len(checkdone) > 0: 
                                                isdone=1
                                                rclonetxt='rcloneMicList_%0.i' %(time.time())
                                                if os.path.exists(rclonetxt):
                                                        os.remove(rclonetxt)
                                                if len(check.split('/')) == 1:
                                                        micname=check
                                                if len(check.split('/')) > 1:
                                                        micname=check.split('/')[-1]
                                                if angpix == -1:
                                                        angpix=1

                                                cmd='echo "%s" >> %s' %(newcheck.split('/')[-1],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

                                                if len(kev) > 0:
                                                        cmd='echo "%s_DW.mrc" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                        subprocess.Popen(cmd,shell=True)

                                                cmd='echo "%s_unblur.log" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

                                                cmd='echo "%s_sum.log" >> %s' %(check.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

						cmd='echo "%s_shifts.txt" >> %s' %(check.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

                                                if savemovies == 'True':
                                                        cmd='mv %s/%s/%s_movie.mrc %s/%s/%s_movie.mrcs' %(outdir,destdir,newcheck.split('/')[-1][:-4],outdir,destdir,newcheck.split('/')[-1][:-4])
                                       		        print cmd 
							subprocess.Popen(cmd,shell=True).wait()
						
							cmd='echo "%s_movie.mrcs" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                        subprocess.Popen(cmd,shell=True)

                                                cmd='echo "%s" >> done_list.txt' %(newcheck.split('/')[-1])
                                                subprocess.Popen(cmd,shell=True)

                                                uploadRsync('%s/%s' %(outdir,destdir),'%s'%(micBucketName),rclonetxt,int(numToGet),newcheck, '%s/%s' %(destdir,check.split('/')[-1]),'%s_movie.mrcs' %(newcheck[:-4]),'%s_bin.mrc' %(newcheck[:-4]),fincounter+group1_f,fincounter+group1_f)
						fincounter=fincounter+1	
					
	movieCounter=movieCounter+numThreads			


