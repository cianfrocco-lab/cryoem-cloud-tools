##################################
####### AWS Information ##########
##################################

#Instructions: 

#1. Please provide the required information (shown below; INPUT REQUIRED)

#2. Once filled out, place this file in a different directory so that later updates to the repository do not overwrite your information. E.g. - we usually place this file and the keypair into the directory $HOME/.aws/

#3. Into your environment initialization script (.bashrc, .cshrc, or .bash_profile) include this line: 
#$ source path/to/aws_init.sh 

#AWS credentials 
export AWS_ACCESS_KEY_ID= #INPUT REQUIRED
export AWS_SECRET_ACCESS_KEY= #INPUT REQUIRED
export AWS_ACCOUNT_ID= #INPUT REQUIRED
export AWS_DEFAULT_REGION= #INPUT REQUIRED
export KEYPAIR_PATH= #INPUT REQUIRED

#Research group name
export RESEARCH_GROUP_NAME= #INPUT REQUIRED: no capital letters or punctuation (e.g. leschziner)

#Set paths
export AWS_DIR= #INPUT REQUIRED

#Set lifetime values for EBS and S3: Number of days, after which they will be deleted  
export EBS_LIFETIME=14
export S3_LIFETIME=12

#Set environment
source $AWS_DIR/aws_aliases.sh
