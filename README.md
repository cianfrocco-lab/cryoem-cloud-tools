# AWS
Software to interface with AWS through easy command line inputs

## Getting started
For each user, you will create a hidden directory in their home directory into which you will add the aws_init.sh file and their keypair.  

* Create hidden folder: 
<pre>$ mkdir /home/[user]/.aws</pre>

* Copy aws_init.sh file & edit to include credentials 

* Add the following line to .bashrc file: 
<pre>source /home/[user]/.aws/aws_init.sh</pre>


