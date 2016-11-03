# AWS
Software to interface with AWS through easy command line inputs

*Contents:*
* [Getting started] (https://github.com/leschzinerlab/AWS#getting-started)
	* [Software dependences] (https://github.com/leschzinerlab/AWS#software-dependencies)
	* [Environment setup] (https://github.com/leschzinerlab/AWS#environment-setup)
* [Usage] (https://github.com/leschzinerlab/AWS#usage)

## Getting started

###Software dependencies 
You'll need to install *pip*, *aws cli* and *fabric*: 
* **pip**: 
	* https://pypi.python.org/pypi/pip
* **aws cli**:
	* http://docs.aws.amazon.com/cli/latest/userguide/installing.html#install-with-pip
	* <pre>$ sudo pip install awscli</pre>
* **fabric**: 
	* http://www.fabfile.org/installing.html
	* <pre>$ sudo pip install fabric</pre>

###Environment setup
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
	* Example usage: 
		* <pre>$ awsls
		InstanceID	Status
		-------------------------------
		i-c29e13cc	terminated
		i-c33e14dd	running</pre>

* **awslaunch**
	* Command to launch instance, configuring security group into VPC automatically to only allow users IP address for incoming SSH traffic.
	* Example usage: 
		* <pre>$ awslaunch
		Usage: awslaunch --instance=<instanceType>
		Options:
  		-h, --help         show this help message and exit
  		--instance=STRING  Specify instance type to launch
  		--instanceList     Flag to list available instances
  		-d                 debug
		$ awslaunch --instance=t2.micro
		Launching AWS instance t2.micro for user keyName_virginia
		Configuring security settings ...
		Booting up instance ...
		Waiting for instance to pass system checks ...
		Instance is ready! To log in:
		ssh -i /home/[user]/.aws/keyName_virginia.pem ubuntu@54.209.133.219</pre>

* **awskill**
	* Command to terminate running instance 
	* Example usage: 
		<pre>$ awskill
		Usage: awskill [instance ID]
		Specify instance ID that will be terminated, which can be found using "awsls"</pre>
		<pre>$ awskill i-112k43e
		Terminate instance i-112k43e? [Y/n] Y
		Removing instance ...</pre>
