
# CPTAC3 CDAP Execution

Note: These instructions presume a Linux-based x86_64 server, with these instructions developed on CentOS7, with sufficient disk-space to support the various working and result files. 

## Work directory setup

1. Establish a working directory. Where necesary, we will specify this working directory as `$CPTAC_CDAP_ROOT`.

2. Download and unpack the CPTAC3 CDAP execution infrastructure.

    % cd $CPTAC_CDAP_ROOT
    % wget -O - -q http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com/cptac-galaxy-setup.sh | sh

3. Configure the CPTAC3 CDAP execution infrastructure for AWS.

    % cd $CPTAC_CDAP_ROOT/cptac-galaxy
    % ./configure
    AWS Access Key: XXXXXXXXXXXXXXXXXXXX
    AWS Secret Key: YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
    Galaxy Account Email: ZZZ@WWW.VVV
    CPTAC DCC Username (Optional): UUUUUU
   
4. 
