#AWS credentials 
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_ACCOUNT_ID=
export AWS_DEFAULT_REGION=us-east-1

#Availability zone
export KEYPAIR_PATH=

#AWS CLI directory
export AWS_CLI_DIR=/home/michaelc/Scripts/AWS/
##List all instances for given user (based on tag)
alias awsls=$AWS_CLI_DIR/list_instances.py
##Kill specified instance 
alias awskill=$AWS_CLI_DIR/kill_instance.py 
##Alias launch command
alias awslaunch=$AWS_CLI_DIR/launch_AWS_instance.py
#Create volume
alias aws_ebs_create=$AWS_CLI_DIR/create_volume.py
#Delete volume
alias aws_ebs_delete=$AWS_CLI_DIR/kill_volume.py


