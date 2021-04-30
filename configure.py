#!bin/python

import ConfigParser, os, os.path, sys

configfilename = '.galaxy'
gensec = 'GENERAL'
# DEFAULT_TOOLS_VERSION = 'CPTAC-GALAXY'

# scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]
# assert os.cwd() == scriptdir, "Please run configure.py in the cptac-galaxy directory"

config = ConfigParser.SafeConfigParser()
if os.path.exists('.galaxy.ini'):
    config.read(['.galaxy.ini'])
    assert config.has_section(gensec)
else:
    config.add_section(gensec)

def getvalue(key,prompt,default=None,advanced=True,checkfile=False):
    origprompt = prompt
    if config.has_option(gensec,key):
	default = config.get(gensec,key)
    if default:
	prompt += " [%s]"%(default,)
    if not advanced and default != None:
	return default
    prompt += ": "
    value = raw_input(prompt).strip()
    if not value:
	if default != None:
	    return default
        else:
	    raise RuntimeError("%s required",origprompt)
    if value == "-" and default:
	return ""
    if value and checkfile:
	if not  os.path.exists(value):
	    raise RuntimeError("%s: %s does not exist"%(prompt,value))
	else:
	    value = os.path.abspath(value)
    return value

advanced = False
if len(sys.argv) > 1 and sys.argv[1] == '--advanced':
    advanced = True

aws_access_key = getvalue('aws_access_key','AWS Access Key')
aws_secret_key = getvalue('aws_secret_key','AWS Secret Key')
aws_keyname = getvalue('aws_keyname','AWS SSH Key Name',"",advanced)
aws_keypath = getvalue('aws_keypath','AWS SSH Key File (Optional)',"",advanced,checkfile=True)
aws_subnet = getvalue('aws_subnet','AWS VPC Subnet (May be blank)',"",advanced)
inst_type = getvalue('aws_instance_type','AWS Instance Type','m4.xlarge',advanced)
# aws_imageid = getvalue('aws_imageid','AWS Image ID','ami-3be8cd2c',advanced)
storage_size = getvalue('aws_storage_size','AWS Volume Size (Gb)','300',advanced)
ebs_optimized = getvalue('aws_ebs_optimized','AWS EBS Optimized','False',advanced)
admin_email = getvalue('admin_email','Galaxy Account Email')
cptac_login = getvalue('cptac_dcc_user','CPTAC DCC Username (Optional)',"")
if cptac_login:
    cptac_pass = getvalue('cptac_dcc_password','CPTAC DCC Password',"")
else:
    cptac_pass = ""
# baseurl = getvalue('tools_baseurl','CPTAC-Galaxy Resource URL','http://edwardslab.bmcb.georgetown.edu/software/downloads/Galaxy',advanced)
# version = getvalue('tools_version','CPTAC-Galaxy Tools Version',DEFAULT_TOOLS_VERSION,advanced)
# cloudmanbucket = getvalue('cloudman_bucket','Cloudman S3 Bucket','cloudman',advanced)
# galaxyfs = getvalue('galaxy_filesystem','Cloudman Galaxy Filesystem','galaxyFS-20170125',advanced)
# galaxyfs = getvalue('galaxy_filesystem','Cloudman Galaxy Filesystem','galaxyFS-20170622',advanced)

from boto.ec2.connection import EC2Connection
from boto.vpc import VPCConnection
try:
    ec2conn = EC2Connection(aws_access_key,aws_secret_key)
    vpcconn = VPCConnection(aws_access_key,aws_secret_key)
except:
    raise
    print >>sys.stderr, "Cannot connect to AWS using provided access key/secret key."
    sys.exit(1)

if aws_keyname:
    if aws_keypath:
        aws_private_key_path = aws_keypath
    else:
        aws_private_key_path = os.path.join(os.getcwd(),".aws",aws_keyname+".pem")
    awskp = ec2conn.get_key_pair(aws_keyname)
    if not awskp:
        print >>sys.stderr, "Cannot find a AWS EC2 keypair with name %s."%(aws_keyname,)
        sys.exit(1)
    if not os.path.exists(aws_private_key_path):
	print >>sys.stderr, "Cannot find local copy of AWS EC2 private key: %s."%(aws_private_key_path,)
        sys.exit(1)

else:
    aws_keyname = "CPTAC-Galaxy"
    aws_private_key_path = os.path.join(os.getcwd(),".aws",aws_keyname+".pem")
    awskp = ec2conn.get_key_pair(aws_keyname)
    if not awskp or not os.path.exists(aws_private_key_path):
	attempt = 0
        awskp = ec2conn.get_key_pair(aws_keyname)
	while awskp:
	    attempt += 1
	    aws_keyname = "CPTAC-Galaxy-%d"%(attempt,)
	    awskp = ec2conn.get_key_pair(aws_keyname)
        aws_private_key_path = os.path.join(os.getcwd(),".aws",aws_keyname+".pem")
	awskp = ec2conn.create_key_pair(aws_keyname)
	try:
	    os.makedirs(".aws")
	except OSError:
	    pass
	awskp.save(".aws")
	aws_keypath = aws_private_key_path

aws_az = ""
if not aws_subnet:
    for vpc in vpcconn.get_all_vpcs():
	if vpc.is_default:
            for sn in vpcconn.get_all_subnets():
	        if sn.vpc_id == vpc.id:
	            aws_subnet = sn.id
	            aws_az = sn.availability_zone
	            break
	    if aws_subnet:
		break
else:
    try:
        sn = vpcconn.get_all_subnets(subnet_ids=[aws_subnet])[0]
	aws_az = sn.availability_zone
    except:
	print >>sys.stderr, "Cannot find a AWS VPC subnet with id %s."%(aws_subnet,)
        sys.exit(1)

config.set(gensec,'aws_access_key',aws_access_key)
config.set(gensec,'aws_secret_key',aws_secret_key)
config.set(gensec,'aws_keyname',aws_keyname)
config.set(gensec,'aws_keypath',aws_keypath)
config.set(gensec,'aws_subnet',aws_subnet)
config.set(gensec,'aws_availability_zone',aws_az)
config.set(gensec,'aws_instance_type',inst_type)
# config.set(gensec,'aws_imageid',aws_imageid)
config.set(gensec,'aws_storage_size',storage_size)
config.set(gensec,'aws_ebs_optimized',ebs_optimized)
config.set(gensec,'admin_email',admin_email)
config.set(gensec,'cptac_dcc_user',cptac_login)
config.set(gensec,'cptac_dcc_password',cptac_pass)
# config.set(gensec,'tools_baseurl',baseurl)
# config.set(gensec,'tools_version',version)
# config.set(gensec,'cloudman_bucket',cloudmanbucket)
# config.set(gensec,'galaxy_filesystem',galaxyfs)

wh = open('.galaxy.ini','w')
config.write(wh)
wh.close()
