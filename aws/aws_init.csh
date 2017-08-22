##################################
####### AWS Information ##########
##################################

#MODIFIED BY CJN FOR CSH INSTEAD OF BASH - 08/22/2017

#Instructions: 

#1. Please provide the required information (shown below; INPUT REQUIRED)

#2. Once filled out, place this file in a different directory so that later updates to the repository do not overwrite your information. E.g. - we usually place this file and the keypair into the directory $HOME/.aws/

#3. Into your environment initialization script (.bashrc, .cshrc, or .bash_profile) include this line: 
#$ source path/to/aws_init.csh 

#AWS credentials 
##Example line: 
###setenv AWS_ACCESS_KEY_ID 111111111


setenv AWS_ACCESS_KEY_ID  #INPUT REQUIRED
setenv AWS_SECRET_ACCESS_KEY #INPUT REQUIRED
setenv AWS_ACCOUNT_ID  #INPUT REQUIRED
setenv AWS_DEFAULT_REGION #INPUT REQUIRED AWS regions that have GPUs: us-west-2 (Oregon), us-east-1 (Virgina), eu-west-1 (Ireland)
setenv KEYPAIR_PATH #INPUT REQUIRED

#Research group name
setenv RESEARCH_GROUP_NAME  #INPUT REQUIRED: no capital letters or punctuation (e.g. leschziner)

#Set paths
setenv AWS_DIR #INPUT REQUIRED

#Set lifetime values for EBS and S3: Number of days, after which they will be deleted  
setenv EBS_LIFETIME 14
setenv S3_LIFETIME 12

#Set environment
source $AWS_DIR/aws_aliases.csh
source ~/CloudSoftwareTools/external_software.csh
