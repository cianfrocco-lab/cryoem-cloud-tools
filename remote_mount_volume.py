#!/usr/bin/env python

import subprocess 
import time

#====================
def module_exists(module_name):
        try:
                __import__(module_name)
        except ImportError:
                return False
        else:
                return True

#====================
def exec_remote_cmd(cmd):
    with hide('output','running','warnings'), settings(warn_only=True):
        return run(cmd)

#======================
def AttachMountEBSVol(instanceID,volID,PublicIP,keyPath):

   #List instances given a users tag
   keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()

   tag=keyPath.split('/')[-1].split('.')[0]

   print '\nAttaching volume %s to instance %s ...\n' %(volID,instanceID)

   volID=subprocess.Popen('aws ec2 attach-volume --volume-id %s --instance-id %s --device xvdf' %(volID,instanceID),shell=True, stdout=subprocess.PIPE).stdout.read().strip()

   time.sleep(10)
   env.host_string='ubuntu@%s' %(PublicIP)
   env.key_filename = '%s' %(keyPath)
   dir_exists=exec_remote_cmd('ls /data')
   if len(dir_exists.split()) >0: 
	if dir_exists.split()[2] == 'access': 
		mk=exec_remote_cmd('sudo mkdir /data/') 
   mount_out=exec_remote_cmd('sudo mount /dev/xvdf /data') 
   print '\n...volume %s mounted onto /data/ ...\n'

#==============================
if __name__ == "__main__":

    fabric_test=module_exists('fabric.api')
    if fabric_test is False:
        print 'Error: Could not find fabric installed and it is required. Install from here: http://www.fabfile.org/installing.html'
        sys.exit()
    #Import Fabric modules now: 
    from fabric.operations import run, put
    from fabric.api import env,run,hide,settings
    from fabric.context_managers import shell_env
    from fabric.operations import put

    keyPath=subprocess.Popen('echo $KEYPAIR_PATH',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
    if len(keyPath) == 0:
        print '\nError: KEYPAIR_PATH not specified as environment variable. Exiting\n'
        sys.exit()

    instanceID='i-050308c7bfc8e3336'
    volID='vol-cd7cbb58'
    PublicIP='35.166.61.35'
    AttachMountEBSVol(instanceID,volID,PublicIP,keyPath)


