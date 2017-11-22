#!/usr/bin/env python
import shutil
import sys 
import subprocess
import os
from pkgutil import iter_modules

homepath=os.environ['HOME']
cloudtoolsonly=False
forceinstall=False

#Specify install location
if len(sys.argv) == 1: 
	install_location='%s/CloudSoftwareTools' %(homepath)		
if len(sys.argv) == 2: 
	if sys.argv[1] == '-h': 
		print 'Usage: ./install_cloud_tools.py'
		print '\nBy default, the program will install the software into %s/CloudSoftwareTools.' %(homepath)
		print '\nTo specify an alternative installation path, specify --prefix {new install path}'
		print '\nThis program will check if the following programs are installed and then install any missing packages:'
		print '\t* cryoem-cloud-tools'
		sys.exit()

	if sys.argv[1] != '-h':
		if sys.argv[1] != '--cloudToolsOnly' and sys.argv[1] != '--force':
 
			print 'Usage: ./install_cloud_tools.py'
	                print '\nBy default, the program will install the software into %s/CloudSoftwareTools.' %(homepath)
        	        print '\nTo specify an alternative installation path, specify --prefix {new install path}'
                	print '\nThis program will check if the following programs are installed and then install any missing packages:'
                	print '\t* cryoem-cloud-tools'
                	sys.exit()

		if sys.argv[1] == '--cloudToolsOnly': 
			cloudtoolsonly=True
			install_location='%s/CloudSoftwareTools' %(homepath)
		
		if sys.argv[1] == '--force':
			install_location='%s/CloudSoftwareTools' %(homepath)
                        forceinstall=True

if len(sys.argv) == 3: 
	if sys.argv[1] != '--prefix': 
		print 'Error: Unknown option %s. Was expecting --prefix' %(sys.argv[1])
		sys.exit()
	install_location='%s' %(sys.argv[2])

if len(sys.argv) == 4:
	counter=0
	for in1 in sys.argv: 
		if in1 == '--prefix': 
			install_location=sys.argv[counter]
		if in1 == '--cloudToolsOnly': 
			cloudtoolsonly=True
		if in1 == '--force': 
			forinstall=True
		counter=counter+1

#==============================
def query_yes_no(question, default="no"):
        valid = {"yes": True, "y": True, "ye": True,"no": False, "n": False}
        if default is None:
                prompt = " [y/n] "
        elif default == "yes":
                prompt = " [Y/n] "
        elif default == "no":
                prompt = " [y/N] "
        else:
                raise ValueError("invalid default answer: '%s'" % default)
        while True:
                sys.stdout.write(question + prompt)
                choice = raw_input().lower()
                if default is not None and choice == '':
                        return valid[default]
                elif choice in valid:
                        return valid[choice]
                else:
                        sys.stdout.write("Please respond with 'yes' or 'no' "
                                         "(or 'y' or 'n').\n")

answer=query_yes_no("\nInstall cryoem-cloud-tools at location %s?" %(install_location))
if answer is False: 
	sys.exit()
print ''

#Default install location: 
if os.path.exists(install_location): 
	answer=query_yes_no("\nDestination directory %s already exists. Overwrite?" %(install_location))
	if answer is False: 
		sys.exit()
	shutil.rmtree(install_location)

os.makedirs(install_location)

uname=subprocess.Popen('uname',shell=True, stdout=subprocess.PIPE).stdout.read().strip() 

#Check if xcode is installed
if uname == 'Darwin': 
	xcode=subprocess.Popen('which xcodebuild',shell=True, stdout=subprocess.PIPE).stdout.read().strip() 
	if len(xcode) == 0: 
		print 'Could not find xcode tools. Please install and try again.'
		print 'To learn how to install xcode: https://developer.apple.com/xcode/'
		sys.exit() 
#Check if AWS CLI is installed
awscli=subprocess.Popen('which aws',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
if len(awscli) == 0: 
	print 'Could not find AWS CLI installed. Please install and try again:'
	print '$ pip install awscli'
	sys.exit()

#Git clone git@github.com:leschzinerlab/cryoem-cloud-tools.git
needGIT=True
git=subprocess.Popen('which git',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
if len(git) > 0: 
	needGIT=False
if len(git) == 0: 
	print 'Error: could not find git install on this system. Install and try again'
	sys.exit()

#CHeck if outside connect exists
hostname = "google.com"
response = os.system("ping -q -c 1 " + hostname)
if response == 0:
	pingstatus = 'OK'
else:
	pingstatus = 'bad'

if pingstatus == 'bad': 
	if forceinstall is False: 
		#print 'Error: Cannot connect to internet. Check your networking and try again'
		#sys.exit()
		print("Error: Cannot ping google.com. This may because of firewall settings. Continuing anyway.")

#Write environmental variables into text file
o1=open('%s/external_software.init' %(install_location),'w')
if uname == 'Darwin':
	o1.write('export PATH=/usr/local/relion/build/bin:$PATH\n' )
	o1.write('export LD_LIBRARY_PATH=/usr/local/relion/build/lib:$LD_LIBRARY_PATH\n')
o1.close()

cmd='git clone https://github.com/cianfrocco-lab/cryoem-cloud-tools.git %s/cryoem-cloud-tools/' %(install_location)
subprocess.Popen(cmd,shell=True).wait()

#Copy aws_init.sh into install_location
o1=open('%s/cryoem-cloud-tools/aws/aws_init.sh' %(install_location),'r')
newout=open('%s/aws_init.sh' %(install_location),'w')

for line in o1: 
	if 'export AWS_DIR' in line: 
		l=line.split('=')
		l[1]='%s/cryoem-cloud-tools' %(install_location)
		line='='.join(l)+'\n'
	if 'aws_aliases.sh' in line: 
		if uname == 'Linux': 
			line='source $AWS_DIR/aws_aliases_linux.sh\n'
		if uname == 'Darwin': 
			line='source $AWS_DIR/aws_aliases_osx.sh\n'
	newout.write(line)
newout.write('source %s/external_software.init' %(install_location))
o1.close()
newout.close()

#Print final message
print '\n\n'
print 'Installation complete! Software can be found in %s\n' %(install_location)
print 'Only a few more steps to finish: \n'
if uname == 'Darwin':
	print '\n1.) Please add the following line to the file %s/.bash_profile\n' %(homepath)
	print 'source %s/aws_init.sh' %(install_location)

if uname == 'Linux': 
	print '\n1.) Please add the following line to the file %s/.bashrc or %s/.cshrc\n' %(homepath,homepath)
        print 'source %s/aws_init.sh' %(install_location)
print '\n2.) Download AWS keypair and put it in a secure location (e.g. %s/)' %(install_location)
print '\n3.) Open and edit the file %s/aws_init.sh\n' %(install_location)
print 'Place your information for AWS into the lines indicated: #INPUT REQUIRED'
print '\n4.) Install AWSCLI: $ pip install awscli OR $ easy_install awscli'
if uname == 'Linux':
	print '\n5.) Install Relion-2.0:'
	print '\nFor Ubuntu:'
	print '$ sudo apt-get update'
	print '$ sudo apt-get install openmpi-bin build-essential libx11-dev libextutils-f77-perl libopenmpi-dev libcr-dev mpich mpich-doc build-essential git cmake libqt4-dev libphonon-dev python2.7-dev libxml2-dev libfltk-gl1.3 libfftw3-double3'
	print '$ git clone https://github.com/3dem/relion.git'
	print '$ cd relion/'
	print '$ mkdir build'
	print '$ cd build/'
	print '$ cmake -DCMAKE_INSTALL_PREFIX=%s/cryoem-cloud-tools/external_software/relion-2.0-linux/ ..' %(install_location)
	print '$ make -j4'
	print '$ make install'
	print '\nNOTE: If you do not put Relion software into directory listed above, update the software environment paths in the file %s/external_software.sh'
if uname == 'Darwin': 
	print '\n5. Copy and paste this command into your terminal. Requires root access:'
	print 'mv %s/cryoem-cloud-tools/external_software/relion /usr/local/' %(install_location)
