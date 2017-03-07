#!/usr/bin/env python
import shutil
import sys 
import subprocess
import os
from pkgutil import iter_modules

homepath=os.environ['HOME']
cloudtoolsonly=False

#Specify install location
if len(sys.argv) == 1: 
	install_location='%s/CloudSoftwareTools' %(homepath)		
if len(sys.argv) == 2: 
	if sys.argv[1] == '-h': 
		print 'Usage: ./install_cloud_tools.py'
		print '\nBy default, the program will install the software into %s/CloudSoftwareTools.' %(homepath)
		print '\nTo specify an alternative installation path, specify --prefix {new install path}'
		print '\nThis program will check if the following programs are installed and then install any missing packages:'
		print '\t* relion2.0'
		print '\t* openmpi'
		print '\t* cryoem-cloud-tools'
		print '\t* fabric'
		print '\t* awscli' 
		print '\nIf you only want to install cryoem-cloud-tools (not relion, openmpi, etc.), include the option --cloudToolsOnly\n'
		sys.exit()

	if sys.argv[1] != '-h':
		if sys.argv[1] != '--cloudToolsOnly':
 
			print 'Usage: ./install_cloud_tools.py'
	                print '\nBy default, the program will install the software into %s/CloudSoftwareTools.' %(homepath)
        	        print '\nTo specify an alternative installation path, specify --prefix {new install path}'
                	print '\nThis program will check if the following programs are installed and then install any missing packages:'
	                print '\t* relion2.0'
        	        print '\t* openmpi'
                	print '\t* cryoem-cloud-tools'
	                print '\t* fabric'
        	        print '\t* awscli'
                	print '\nIf you only want to install cryoem-cloud-tools (not relion, openmpi, etc.), include the option --cloudToolsOnly\n'
                	sys.exit()

		if sys.argv[1] == '--cloudToolsOnly': 
			cloudtoolsonly=True
			install_location='%s/CloudSoftwareTools' %(homepath)
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
'''
#Check if anaconda is installed
if uname == 'Darwin': 
	conda='which conda',shell=True, stdout=subprocess.PIPE).stdout.read().strip() 
	if len(conda) > 0: 
		print 'anaconda python is installed. Please remove from environment and try again'
		print 'To do this, comment out any lines for anaconda in your .bash_profile'
		sys.exit()
'''
'''
pip=subprocess.Popen('which pip',shell=True, stdout=subprocess.PIPE).stdout.read().strip() 

if cloudtoolsonly is False: 
	if len(pip) == 0: 
		print 'Could not find pip. Please install pip and try again:'
		print '$ sudo easy_install pip'
		sys.exit()

#Check fabric installation
needFabric=False
try: 
	import fabric.api
except ImportError:
	needFabric = True

#Check aws cli installation
needAWSCLI=True
aws_version=subprocess.Popen('which aws',shell=True, stdout=subprocess.PIPE).stdout.read().strip()	
if len(aws_version) > 0: 
	needAWSCLI=False
'''
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
	print 'Error: Cannot connect to internet. Check your networking and try again'
	sys.exit()
#Check relion
'''
installRelion=True
relion=subprocess.Popen('which relion',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
if len(relion) > 0: 
	installRelion=False

if installRelion is True: 
        gcc=subprocess.Popen('which gcc',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
        if cloudtoolsonly is False: 
		if len(gcc) == 0: 
                	print 'Error: gcc is needed to compile Relion. Please download and try again'
                	sys.exit()
	if needGIT is True:
        	print 'Install git: https://git-scm.com/download/mac and try again.'
	        sys.exit()
	#Check for mpi
	installMPI=True
	mpi=subprocess.Popen('which mpirun',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	if len(mpi) > 0: 
		installMPI=False
	cmakepath=subprocess.Popen('which cmake',shell=True, stdout=subprocess.PIPE).stdout.read().strip()
	if cloudtoolsonly is False: 
		if len(cmakepath) == 0:
			if uname == 'Darwin': 
				if os.path.exists('/Applications/CMake.app/Contents/bin/cmake'): 
					cmakepath='/Applications/CMake.app/Contents/bin/cmake'
				if not os.path.exists('/Applications/CMake.app/Contents/bin/cmake'): 
					print '\nError: could not find the compiler cmake installed. Please install and try again'
					if uname == 'Darwin': 
						print 'For MacOSX, you can download Cmake here: https://cmake.org/download/\n'
					sys.exit()

#Make directorioes
os.makedirs('%s/awscli/' %(install_location))
os.makedirs('%s/awscli/bin/' %(install_location))
if cloudtoolsonly is False:
	os.makedirs('%s/fabric' %(install_location))
if needAWSCLI is True: 
	cmd='curl -s "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"'
	subprocess.Popen(cmd,shell=True).wait()
	if not os.path.exists('awscli-bundle.zip'): 
		print 'Error: Was unable to download awscli software. Exiting'
		sys.exit()
	cmd='unzip -qq awscli-bundle.zip'
	subprocess.Popen(cmd,shell=True).wait()
	shutil.move('awscli-bundle','%s/awscli' %(install_location))
	os.remove('awscli-bundle.zip')
	cmd='%s/awscli/awscli-bundle/install -b %s/awscli/bin/aws' %(install_location,install_location)
	subprocess.Popen(cmd,shell=True).wait()
	shutil.rmtree('%s/awscli/awscli-bundle' %(install_location))
if cloudtoolsonly is False:
	if needFabric is True: 
		cmd='pip install --install-option="--prefix=%s/fabric" fabric' %(install_location)
		subprocess.Popen(cmd,shell=True).wait()
'''
cmd='git clone https://github.com/leschzinerlab/cryoem-cloud-tools.git %s/cryoem-cloud-tools/' %(install_location)
subprocess.Popen(cmd,shell=True).wait()
'''
if cloudtoolsonly is False:

	if installRelion is True: 
			
		cmd='git clone https://github.com/3dem/relion.git'
		subprocess.Popen(cmd,shell=True).wait()

		o11=open('installrelion.sh','w')
		if installMPI is True: 
			o11.write('export LD_LIBRARY_PATH=%s/cryoem-cloud-tools/external_software/openmpi-2.0.2/lib/:$LD_LIBRARY_PATH\n' %(install_location))
			o11.write('export PATH=%s/cryoem-cloud-tools/external_software/openmpi-2.0.2/bin/:$PATH\n' %(install_location))
		o11.write('cd relion/\n')
		o11.write('mkdir build\n ')
		o11.write('cd build\n ')
		o11.write('%s ..\n' %(cmakepath))
		o11.write('make\n')
		o11.close()

		cmd='chmod +x installrelion.sh'
		subprocess.Popen(cmd,shell=True).wait()
	
		cmd='./installrelion.sh'
		subprocess.Popen(cmd,shell=True).wait()
		
		cmd='mv relion/ %s/relion2.0' %(install_location)
		subprocess.Popen(cmd,shell=True).wait()
	
		os.remove('installrelion.sh')
'''
#Write environmental variables into text file
o1=open('%s/external_software.init' %(install_location),'w')
#if cloudtoolsonly is False: 
#	if needFabric is True: 
#		o1.write('export PATH=%s/fabric/bin:$PATH\n' %(install_location))
#		o1.write('export PYTHONPATH=%s/fabric/lib/python2.7/site-packages/:$PYTHONPATH\n' %(install_location))
#if needAWSCLI is True:
o1.write('export PATH=%s/cryoem-cloud-tools/external_software/aws/bin/:$PATH\n' %(install_location))
o1.write('export PYTHONPATH=%s/cryoem-cloud-tools/external_software/aws/lib/python2.7/site-packages/\n' %(install_location))
#if installRelion is True: 
o1.write('export PATH=%s/cryoem-cloud-tools/external_software/relion-2.0-mac/bin/:$PATH\n' %(install_location))
o1.write('export LD_LIBRARY_PATH=%s/cryoem-cloud-tools/external_software/relion-2.0-mac/lib:$LD_LIBRARY_PATH\n' %(install_location))
#if cloudtoolsonly is False: 
#	if installMPI is True: 
#		o1.write('export PATH=%s/relion2.0/external_software/openmpi-2.0.2/bin:$PATH\n' %(install_location))
#		o1.write('export LD_LIBRARY_PATH=%s/relion2.0/external_software/openmpi-2.0.2/lib:$LD_LIBRARY_PATH\n' %(install_location))
o1.close()

#Copy aws_init.sh into install_location
o1=open('%s/cryoem-cloud-tools/aws/aws_init.sh' %(install_location),'r')
newout=open('%s/aws_init.sh' %(install_location),'w')

for line in o1: 
	if 'export AWS_DIR' in line: 
		l=line.split('=')
		l[1]='%s/cryoem-cloud-tools' %(install_location)
		line='='.join(l)+'\n'
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
print 'Place your information for AWS into the lines indicated: #INPUT REQUIRED\n'

