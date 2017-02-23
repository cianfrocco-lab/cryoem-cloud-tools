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

motioncor2path='/home/EM_Packages/MotionCor2/MotionCor2-08-22-2016'
motioncorrpath='/home/EM_Packages/motioncorr_v2.1/bin/dosefgpu_driftcorr'
unblurpath='/home/EM_Packages/unblur_1.0.2/bin/unblur_openmp_7_17_15.exe'
summoviepath='/home/EM_Packages/summovie_1.0.2/bin/sum_movie_openmp_7_17_15.exe'
relionpath='/home/EM_Packages/relion2-beta/build/bin/relion_run_motioncorr'
relionhandler='/home/EM_Packages/relion2-beta/build/bin/relion_image_handler'

def writeRunUnBlurSum(relioncmd,micname,additionalcmds,totframes): 
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
			lastframesum=relioncmd.split()[counter+1]
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

	if os.path.exists(scriptrun): 
		os.remove(scriptrun)
	o1=open(scriptrun,'w')
	o1.write('#!/usr/bin/env bash\n')
	#o1.write('export  OMP_NUM_THREADS=4\n')
	o1.write('/home/EM_Packages/unblur_1.0.2/bin/unblur_openmp_7_17_15.exe > %s << EOF\n' %(unblurlog))
	o1.write('%s\n' %(micname))
	o1.write('%s\n' %(totframes))
 	o1.write('%s\n' %(outmicname))
	o1.write('%s\n' %(shifts))
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
	if savemovies is False: 
		o1.write('NO\n')
	o1.write('NO\n')
	o1.write('EOF\n')
	o1.write('\n')
	o1.write('/home/EM_Packages/summovie_1.0.2/bin/sum_movie_openmp_7_17_15.exe > %s << EOF\n' %(sumlog))
	o1.write('%s\n' %(micname))
	o1.write('%s\n' %(totframes))
	o1.write('%s\n' %(outmicname))
	o1.write('%s\n' %(shifts))
	o1.write('%s_frc.txt\n' %(shifts[:-4]))
	o1.write('%s\n' %(firstframe))
	o1.write('%s\n' %(lastframesum))
	o1.write('%s\n' %(apix))
	if doseweight is False: 
		o1.write('NO\n')
	if doseweight is True: 
		o1.write('YES\n')
		o1.write('%s\n' %(doseperframe))
		o1.write('%s\n' %(voltage))
		o1.write('%s\n' %(prexpose))
		o1.write('YES\n')
	o1.write('EOF\n')
	o1.close()
	cmd='chmod +x %s' %(scriptrun)
	subprocess.Popen(cmd,shell=True).wait()

	cmd='./%s' %(scriptrun)
	subprocess.Popen(cmd,shell=True)

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
#Get initial round of mics
counter=0
miclist=[]
if len(destdir) > 0: 
	if not os.path.exists(destdir): 
		os.makedirs(destdir)
if os.path.exists('rcloneMicList.txt'): 
	os.remove('rcloneMicList.txt')
r1=open('rcloneMicList.txt','w')
while counter < int(numFilesAtATime): 
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
cmd='~/rclone sync rclonename:%s %s/ --quiet --include-from rcloneMicList.txt --transfers %i' %(movieBucket,destdir,int(numFilesAtATime))
subprocess.Popen(cmd,shell=True).wait()
os.remove('rcloneMicList.txt')
movieCounter=0
while movieCounter < len(movielist): 
	threadnum=0
	outCheckList=[]
	movieDLchecklist=[]
	while threadnum < numThreads: 
		micnum=movieCounter+threadnum
		if micnum >=len(movielist): 
			threadnum=threadnum+1
		if micnum < len(movielist): 
			#select single line from relion mic star file 
			micname=movielist[micnum].strip()
			additionalcmds=''
			if micnum == 0:	
				cmd='/home/EM_Packages/relion2-beta/build/bin/relion_image_handler --i %s --stats > handler.txt' %(micname)
				subprocess.Popen(cmd,shell=True).wait()
				outline=linecache.getline('handler.txt',1).split('=')[1].split('x')[2]
				#lastframe=subprocess.Popen('relion_image_handler --i %s --stats' %(micname),shell=True, stdout=subprocess.PIPE).stdout.read().strip().split('=')[1].split('x')[2]
			if aligntype == 'unblur': 
				additionlcmds=additionalcmds+' --use_unblur'+' --unblur_exe %s' %(unblurpath)+' --summovie_exe %s' %(summoviepath)+' --j 1'
			if aligntype == 'motioncorr':
				additionalcmds=additionalcmds+' --motioncorr_exe %s' %(motioncorrpath)
			if aligntype == 'motioncor2': 
				additionalcmds=additionalcmds+' --motioncorr_exe %s' %(motioncor2path)+' --use_motioncor2'+' --gpu %i' %(threadnum)
			if gainref != '-1': 
				additionalcmds=additionalcmds+' --gainref %s' %(gainref)
			
			if aligntype != 'unblur': 
				cmd='nohup %s --i %s' %(relionpath,micname)+' '+relioncmd+' '+additionalcmds+' &'
				subprocess.Popen(cmd,shell=True)
			if aligntype == 'unblur': 
				writeRunUnBlurSum(relioncmd,micname,additionalcmds,lastframe)
			newnamesplit=micname.split('.')
			outCheckList.append('%s' %(micname))
	
			if os.path.exists('rcloneMicList_%i.txt' %(threadnum)): 
				os.remove('rcloneMicList_%i.txt' %(threadnum))
			
			nextmicNum=micnum+numThreads+1
			if nextmicNum < len(movielist):
				micname=movielist[nextmicNum]
				if len(micname.split('/')) == 1:
		                	micnameonly=micname.strip()
        			if len(micname.split('/')) > 1:
                			micnameonly=micname.split('/')[-1].strip()
				cmd='echo "%s" >> rcloneMicList_%i.txt' %(micnameonly,threadnum)
				subprocess.Popen(cmd,shell=True).wait()
				cmd='~/rclone sync rclonename:%s %s/ --quiet --include-from rcloneMicList_%i.txt --transfers %i' %(movieBucket,destdir,threadnum,int(numFilesAtATime))	
				subprocess.Popen(cmd,shell=True)
				time.sleep(3)
				movieDLchecklist.append(micname)
				os.remove('rcloneMicList_%i.txt' %(threadnum)) 
			threadnum=threadnum+1

	#Start waiting for 1) jobs to finish and 2) movies have been downloaded
	for check in outCheckList: 
		isdone=0
		newnamesplit=check.split('.')
                if aligntype != 'unblur': 
			if len(newnamesplit) > 2:
	                	del newnamesplit[-1]
                        	newnamesplit='_'.join(newnamesplit)
                       		newmicname=newnamesplit+'.'+micname.split('.')[-1]
                	if len(newnamesplit) == 2:
                        	newmicname=micname
                	newcheck=outdir+'/'+newmicname
			newcheck=newcheck.strip()
		if aligntype == 'unblur': 
			newcheck=outdir+'/'+check
		while isdone == 0:
			time.sleep(3)
			if aligntype != 'unblur': 
				if os.path.exists(newcheck):
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
					cmd='%s --i %s --o %s_bin.mrc --angpix %f --rescale_angpix %f' %(relionhandler,newcheck,newcheck[:-4],angpix,angpix*4)
					subprocess.Popen(cmd,shell=True).wait()

					cmd='echo "%s" >> %s' %(newcheck.split('/')[-1],rclonetxt)
        	                        subprocess.Popen(cmd,shell=True)
	
					cmd='echo "%s_bin.mrc" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                	                subprocess.Popen(cmd,shell=True)

					cmd='echo "%s.out" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                	subprocess.Popen(cmd,shell=True)

					cmd='echo "%s_shifts.eps" >> %s' %(check.split('/')[-1][:-4],rclonetxt)
                                       	subprocess.Popen(cmd,shell=True)

					if savemovies == 'True': 
						cmd='echo "%s_movie.mrcs" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
						subprocess.Popen(cmd,shell=True)

                         	        cmd='~/rclone sync %s/%s %s --quiet --include-from %s --transfers %i' %(outdir,destdir,micBucketName,rclonetxt,int(numFilesAtATime))
                                	subprocess.Popen(cmd,shell=True).wait()
			
					os.remove(newcheck)
					os.remove('%s/%s' %(destdir,check.split('/')[-1]))
					if savemovies == 'True': 
						os.remove('%s_movie.mrcs' %(newcheck[:-4]))
					os.remove('%s_bin.mrc' %(newcheck[:-4]))
					os.remove(rclonetxt)	
			if aligntype == 'unblur': 
				unblurbase=newcheck[:-(len(newcheck.split('.')[-1])+1)]
				if os.path.exists('%s_sum.log' %(unblurbase)):
					checkdone=subprocess.Popen('cat %s_sum.log | grep cleanly' %(unblurbase),shell=True, stdout=subprocess.PIPE).stdout.read().strip()
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
                	                        cmd='%s --i %s --o %s_bin.mrc --angpix %f --rescale_angpix %f' %(relionhandler,newcheck,newcheck[:-4],angpix,angpix*4)
                                	        subprocess.Popen(cmd,shell=True).wait()
	
        	                                cmd='echo "%s" >> %s' %(newcheck.split('/')[-1],rclonetxt)
                	                        subprocess.Popen(cmd,shell=True)
	
        	                                cmd='echo "%s_bin.mrc" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                	                        subprocess.Popen(cmd,shell=True)
	
        	                                cmd='echo "%s_unblur.log" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                	                        subprocess.Popen(cmd,shell=True)

						cmd='echo "%s_sum.log" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

						cmd='echo "%s_shifts.txt" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)
	
						cmd='echo "%s_shifts_frc.txt" >> %s' %(newcheck.split('/')[-1][:-4],rclonetxt)
                                                subprocess.Popen(cmd,shell=True)

						cmd='~/rclone sync %s/%s %s --quiet --include-from %s --transfers %i' %(outdir,destdir,micBucketName,rclonetxt,int(numFilesAtATime))
						subprocess.Popen(cmd,shell=True).wait()

                        	                os.remove(newcheck)
                	                        os.remove('%s/%s' %(destdir,check.split('/')[-1]))
        	                                os.remove('%s_bin.mrc' %(newcheck[:-4]))
	                                        os.remove(rclonetxt)

	movieCounter=movieCounter+numThreads


