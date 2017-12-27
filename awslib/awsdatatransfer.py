import math
import subprocess
import sys
import os
from fabric.api import env,run,hide,settings

#====================
def exec_remote_cmd(cmd):
    from fabric.operations import run, put
    from fabric.api import hide,settings
    with hide('output','running','warnings') and settings(warn_only=True):
        return run(cmd)

#=====================
def transferDirToS3(directoryToTransfer,bucketname,awspath,numfiles,keyid,secretid,region): 
	'''Use rclone to move data onto S3'''

	#Get OSX vs linux versions 
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

	#Copy using rsync
	cmd='%s sync %s rclonename:%s --quiet --transfers %i > rclone.log' %(rclonepath,directoryToTransfer,bucketname,math.ceil(numfiles))
	subprocess.Popen(cmd,shell=True).wait()

	if os.path.exists('%s/rclone.conf' %(directoryToTransfer)): 
		os.remove('%s/rclone.conf' %(directoryToTransfer))
	if os.path.exists('rclone.log'):
                os.remove('rclone.log')

#===================
def transferS3toVM(IP,keypair,bucketname,dironebs,rclonepath,keyid,secretid,region,numfilesAtATime,maxFileSize):

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
        exec_remote_cmd('%s/%s copy rclonename:%s %s --max-size %iG --quiet --transfers %i' %(homedir,rcloneexe,bucketname.split('s3://')[-1],dironebs,maxFileSize,numfilesAtATime))

	if os.path.exists('rclone.conf'): 
                os.remove('rclone.conf')

	if os.path.exists('rclone.log'):
                os.remove('rclone.log')
