# AWS
Software to interface with AWS through easy command line inputs

*Contents:*
* [Getting started] (https://github.com/leschzinerlab/AWS#getting-started)
* [Usage] (https://github.com/leschzinerlab/AWS#usage)

## Getting started
For each user, you will create a hidden directory in their home directory into which you will add the aws_init.sh file and their keypair.  

* Create hidden folder: 
<pre>$ mkdir /home/[user]/.aws</pre>

* Copy aws_init.sh file & edit to include credentials

* Copy keypair into directory, making sure to modify permissions of file using <pre>chmod 600</pre>

* Add the following line to .bashrc file: 
<pre>source /home/[user]/.aws/aws_init.sh</pre>

## Usage
The underlying code is written in python and aliased to simple commands: awsls, awslaunch, awskill. 

* **awsls**
	* Lists all instances assigned to user, where user instances are assigned based upon being tagged with key pair name as the instance Owner. 

* **awslaunch**
	* Command to launch instance, configuring security group into VPC automatically to only allow users IP address for incoming SSH traffic.
	* Command usage: 
		* <pre>$ awslaunch
		Usage: awslaunch --instance=<instanceType>

Options:
  -h, --help         show this help message and exit
  --instance=STRING  Specify instance type to launch
  --instanceList     Flag to list available instances
  -d                 debug</pre>

* **awskill**
