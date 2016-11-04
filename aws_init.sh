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
#Commands available
alias awshelp=$AWS_CLI_DIR/aws_help.py
#Attach volume
alias aws_ebs_attach=$AWS_CLI_DIR/attach_volume.py
#Attach volume
alias aws_ebs_detach=$AWS_CLI_DIR/detach_volume.py
#List spot price
alias aws_spot_price_history=$AWS_CLI_DIR/list_spot_price.py 



