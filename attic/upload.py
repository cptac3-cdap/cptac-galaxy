#!bin/python
import sys, os, os.path, time
from operator import itemgetter

from optparse import OptionParser
parser = OptionParser()
parser.add_option("--galaxy",dest="url",help="Galaxy server URL")
parser.add_option("--username",dest="user",help="Galaxy user")
parser.add_option("--password",dest="pw",help="Galaxy password")
opts,args = parser.parse_args()

import ftplib

def ftpopen(url,username,password):
    host = url.split('://',1)[1]
    return ftplib.FTP(host,username,password)

def ftpupload(handle,filename):
    h = open(filename,'rb')
    path,base = os.path.split(filename)
    handle.storbinary('STOR %s'%(base,),h)
    h.close()
    return base

def ftpclose(handle):
    handle.close()

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=opts.url,email=opts.user,password=opts.pw)
ftp = ftpopen(opts.url,opts.user,opts.pw)
hi = gi.histories.create_history('Spectra').get('id')
for f in args:
    fn = ftpupload(ftp,f)
    gi.tools.upload_from_ftp(fn, hi)
while True:
    touncompress = 0
    for di in gi.histories.show_matching_datasets(hi):
        if di['name'].endswith('.gz'):
	    touncompress += 1
    if touncompress == 0:
	break
    print "Still %d files to uncompress"%(touncompress,)
    time.sleep(30)
elements = []
for di in gi.histories.show_matching_datasets(hi):
    elements.append(HistoryDatasetElement(di['name'],di['id']))
coldesc = CollectionDescription(name="Spectra",elements=elements)
ci = gi.histories.create_dataset_collection(hi,coldesc)
