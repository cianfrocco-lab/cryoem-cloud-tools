#Set paths
export AWS_CLI_DIR=$AWS_DIR/aws_build_osx/
export AWS_RELION=$AWS_DIR/aws_build_osx/
export AWS_ROSETTA=$AWS_DIR/rosetta/
export PATH=$AWS_CLI_DIR/:$PATH
#export PATH=$AWS_RELION/:$PATH
export PATH=$AWS_ROSETTA/:$PATH
##List all instances for given user (based on tag)
alias awsls=$AWS_CLI_DIR/list_instances
##Kill specified instance 
alias awskill=$AWS_CLI_DIR/kill_instance 
##Alias launch command
alias awslaunch=$AWS_CLI_DIR/launch_AWS_instance
##Alias launch group of instances command
alias awslaunch_movieAlign=$AWS_CLI_DIR/launch_AWS_S3Movie_Alignment
#Create volume
alias aws_ebs_create=$AWS_CLI_DIR/create_volume
#Delete volume
alias aws_ebs_delete=$AWS_CLI_DIR/kill_volume
#Commands available
#Attach volume
alias aws_ebs_attach=$AWS_CLI_DIR/attach_volume
#Attach volume
alias aws_ebs_detach=$AWS_CLI_DIR/detach_volume
#List spot price
alias aws_spot_price_history=$AWS_CLI_DIR/list_spot_price
#Admin list
alias awsls_admin=$AWS_CLI_DIR/list_all
#Launch cluster
alias awslaunch_cluster=$AWS_CLI_DIR/launch_starcluster
#Relion QSUB command
export RELION_QSUB_TEMPLATE=$AWS_DIR/relion/relion_qsub.sh
#Export directory to path
export PATH=$AWS_CLI_DIR/:$PATH
#Create snapshot
alias aws_snapshot_create=$AWS_CLI_DIR/create_snapshot
#Delete snapshot
alias aws_snapshot_delete=$AWS_CLI_DIR/kill_snapshot
