
# CPTAC3 CDAP Execution

Documentation of the steps to run a CPTAC3 CDAP analysis of a CPTAC3 study. Presumes access to the CPTAC private portal (CPTAC Data Exchange Sandbox), contact cptac.dcc.help@esacinc.com for an account if entitled to access this data. Most of the instructions, however, are generic, with only the location of the RAW spectral datafiles requiring private portal access.

These instructions presume a Linux-based x86_64 machine with sufficient disk-space to support the various working and result files. 

A demonstration dataset ("ExampleStudy") has been created for the purpose of this documentation.

The basic steps are:

1. [Establish a CPTAC3 CDAP working directory](#1-establish-a-cptac3-cdap-working-directory)
2. [Create a CPTAC Study working directory](#2-create-a-cptac-study-working-directory)
3. [Launch a new CPTAC3 CDAP Galaxy cluster on AWS](#3-launch-a-new-cptac3-cdap-galaxy-cluster-on-aws)
4. [Execute the CDAP Analysis](#4-execute-the-cdap-analysis)
5. [Terminate the CPTAC3 CDAP Galaxy cluster](#5-terminate-the-cptac3-cdap-galaxy-cluster)

Detailed steps are provided below.

## 1. Establish a CPTAC3 CDAP working directory
1. Establish a working directory. Where necesary, we will specify this working directory as `$CPTAC_CDAP_ROOT`.
2. Download and unpack the CPTAC3 CDAP execution infrastructure for x86_64 Linux. The intrastructure is developed and tested on CentOS7. 
```
% cd $CPTAC_CDAP_ROOT
% wget -O - -q http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com/cptac-galaxy-setup.sh | sh
```
3. Configure the CPTAC3 CDAP execution infrastructure for AWS. You will need AWS credientials and, if the RAW spectral data is at the CPTAC private portal, credentials for login. Use your normal email address for your Galaxy Account Email. 
```
% cd $CPTAC_CDAP_ROOT/cptac-galaxy
% ./configure
AWS Access Key: XXXXXXXXXXXXXXXXXXXX
AWS Secret Key: YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
Galaxy Account Email: ZZZ@WWW.VVV
CPTAC DCC Username (Optional): UUUUUU
CPTAC DCC Password: PPPPPPPP
```
4. Configure the CPTAC DCC command-line scripts in `$CPTAC_CDAP_ROOT/cptac-galaxy/cptacdcc` if the spectral data is at the CPTAC private portal. 
```
% cat > cptac-galaxy/cptacdcc/cptacdcc-local.ini
[Portal]
User = UUUUUU
Password = PPPPPPPP
% cptac-galaxy/cptacdcc/cptacdcc CDAP
Folder: /CDAP
InProgress/     2.58 GB   2021-06-25 15:59:00   edwardna
%
```
5. Note that at any point, you can update the CPTAC3 CDAP infrastructure to the latest version using the update script.
```
% cd $CPTAC_CDAP_ROOT/cptac-galaxy
% ./update.sh
%
```
## 2. Create a CPTAC Study working directory
1. Create working directories for study `ExampleStudy` in `$CPTAC_CDAP_ROOT`.
```
% cd $CPTAC_CDAP_ROOT
% mkdir ExampleStudy
% cd ExampleStudy
% mkdir Proteome
% mkdir Phosphoproteome
%
```
2. Create and edit the the study parameter file. For CPTAC, valid SPECIES values are "Human", "Human+Mouse" (for CPTAC CompRef), "Mouse", "Rat"; valid PROTEOME values are "Proteome", "Phosphoproteome", "Acetylome", "Glycoproteome", and "Ubiquitilome"; valid QUANT values are "Label-Free", "iTRAQ", "TMT6", "TMT10", "TMT11"; and valid INST values are "Thermo Q-Exactive HCD" (for all high-accuracy precursor data-dependent acquisitions on Thermo instruments). Some parameters can be omitted for some analysis types. For a starting template, see [`../template.params`](../template.params). 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cat > ExampleStudy_Proteome.params
SPECIES="Human"
PROTEOME="Proteome"
QUANT="TMT11"
INST="Thermo Q-Exactive HCD"
%
```
3. Create the RAW spectral datafile manifest (depends on placement and data-layout of RAW files on the DCC). Other RAW spectral datafile sources are supported, including local files, public URLs, and AWS S3. A full description of these capabilities and the format of the maifest file can be found [elsewhere](manifest.md). `ExampleStudy_Proteome.RAW.txt` is available for [download](ExampleStudy_Proteome.RAW.txt). Replace `UUUUUU` with your CPTAC private portal username. The `dfcoll.sh` script can automatically construct the manifest file given a CPTAC private portal directory. 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% ../../cptac-galaxy/dfcoll.sh dcc/UUUUUU CDAP/ExampleStudy/MS > ExampleStudy_Proteome.RAW.txt
% cat ExampleStudy_Proteome.RAW.txt
01CPTAC_ExampleStudy_Proteome   dcc/UUUUUU    CDAP/ExampleStudy/MS/01CPTAC_ExampleStudy_Proteome.cksum
02CPTAC_ExampleStudy_Proteome   dcc/UUUUUU    CDAP/ExampleStudy/MS/02CPTAC_ExampleStudy_Proteome.cksum
%
```
4. Create the tab-separated value isotopic labeling batch correction file (see published studies for examples). Find the necesary values by searcing for the TMT reagent lot numbers at [Thermo Fisher](https://www.thermofisher.com/) and copying the values from the Certificate of Analysis PDF. For TMT11, two lot numbers are used (TMT10 + TMT11-131C). Note that the label names for TMT10 use 126 and 131, while the label names for TMT11 use 126C, 131N, 131C.  If the labels batch identifiers are not available use [`Identity_TMT_Label_Correction.txt`](../Identity_TMT_Label_Correction.txt) or for a starting template, use the file [`template.label.txt`](../template.label.txt). `ExampleStudy_Proteome.label.txt` is available for [download](ExampleStudy_Proteome.label.txt).
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cp ../../cptac-galaxy/docs/ExampleStudy_Proteome.label.txt .
% 
```
5. Create the tab-separated values experimental design (sample) file (see published studies for examples). Usually this requires checking the meta-data provided by the data-generators. Headers include: `FileNameRegEx`, `AnalyticalSample`, `LabelReagent`, `Ratios`, and the label names. Values in the LabelRegent column should match one of the batch correction entry names in the `ExampleStudy_Proteome.label.txt` file. Label name headers should match the label names in the batch correction label names. Values in the Ratios column should be separated by commas, and use the label names from the batch correction file. For a starting template, use the file [`template-tmt10.sample.txt`](../template-tmt10.sample.txt) or [`template-tmt11.sample.txt`](../template-tmt11.sample.txt). `ExampleStudy_Proteome.sample.txt` is available for [download](ExampleStudy_Proteome.sample.txt).
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cp ../../cptac-galaxy/docs/ExampleStudy_Proteome.sample.txt .
% 
```
6. A completely setup study directory will have `*.params`, `*.RAW.txt`, `*.label.txt`, and `*.sample.txt` files with a common prefix:
```
% ls
ExampleStudy_Proteome.label.txt
ExampleStudy_Proteome.params
ExampleStudy_Proteome.RAW.txt
ExampleStudy_Proteome.sample.txt
```

## 3. Launch a new CPTAC3 CDAP Galaxy cluster on AWS
1. Launch the cluster. Only one cluster with a given name may be used per AWS account. The cluster should be ready to go in 10-15 mins. 
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/launch CDAP
Password: AAAAAAAAA
[00:04] 
[00:19] IP: XX.XX.XX.XX Status: pending 
[00:34] IP: XX.XX.XX.XX Status: running 
[01:05] IP: XX.XX.XX.XX 
[02:05] IP: XX.XX.XX.XX PSS: Unstarted Galaxy: Unstarted 
[05:08] IP: XX.XX.XX.XX PSS: Unstarted Galaxy: Starting 
[05:53] IP: XX.XX.XX.XX PSS: Unstarted Galaxy: Running 
[06:08] IP: XX.XX.XX.XX PSS: Running Galaxy: Running 
[07:09] IP: XX.XX.XX.XX PSS: Running Galaxy: Starting 
[07:24] IP: XX.XX.XX.XX PSS: Running Galaxy: Running 
[10:40] IP: XX.XX.XX.XX PSS: Completed Galaxy: Running
Disable ProFTPd for security reasons...
Galaxy ready: https://XX.XX.XX.XX
Imported workflow: ...
...
Starting WinPulsar nodes...
Uploading sequence databases...
[02:49] URL: https://XX.XX.XX.XX SeqDB upload: ok(46) running(2) 
[03:13] URL: https://XX.XX.XX.XX SeqDB upload: ok(48) 
Starting sequence database indexing and other setup tasks...
[04:13] URL: https://XX.XX.XX.XX Indexing: queued(22) running(2) Other: queued(1) 
...
[08:12] URL: https://XX.XX.XX.XX Indexing: ok(24) Other: ok(1) 
Setting autoscale, max 2 workers
Indexed sequence databases and auto-scale workers ready.
Windows pulsar nodes will come online shortly.
%
```
## 4. Execute the CDAP Analysis
1. Use the `cptac-galaxy/cluster` program to manage the execution of batch jobs on the AWS cluster. The `cdap` cluster command starts a CDAP batch job. Use `<ctrl>-C` to escape the status output. More information about the `cptac-galaxy/cluster` command is [available](cluster.md). Note that multiple clusters and multiple jobs per cluster can be managed using the `cptac-galaxy/cluster` command, but the example analysis here assumes a single cluster and a single analysis. Note that the analysis may fail if the study parameter files are not formed correctly or because individual steps of the analysis fail. See [troubleshooting](troubleshooting.md) for information about how to recover from problems.
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/cluster cdap ./ExampleStudy/Proteome/ExampleStudy_Proteome.params
[Thu Nov  4 19:44:53 UTC 2021] *** PSM Analysis ***
[Thu Nov  4 19:44:53 UTC 2021] Workflow: CPTAC3-CDAP: MSGF+ TMT 11-plex (Thermo Q-Exactive HCD)
[Thu Nov  4 19:45:53 UTC 2021] Waiting 18, Idle 0, Running 0, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 19:46:53 UTC 2021] Waiting 17, Idle 0, Running 1, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 19:47:53 UTC 2021] Waiting 16, Idle 0, Running 2, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 19:48:53 UTC 2021] Waiting 16, Idle 0, Running 2, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 19:49:53 UTC 2021] Waiting 15, Idle 1, Running 2, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 19:50:53 UTC 2021] Waiting 14, Idle 1, Running 3, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
^C
%
```
2. The `status` cluster command can be used to get the current status of the job. Let the batch job run until the output from `status` indicates the analysis is complete. See [troubleshooting](troubleshooting.md) for information about how to recover from problems.
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/cluster status
...
[Thu Nov  4 20:54:53 UTC 2021] Waiting 4, Idle 0, Running 14, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 20:55:53 UTC 2021] Waiting 4, Idle 0, Running 14, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 20:56:53 UTC 2021] Waiting 3, Idle 1, Running 14, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 20:57:53 UTC 2021] Waiting 3, Idle 1, Running 14, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 20:58:53 UTC 2021] Waiting 2, Idle 1, Running 15, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
[Thu Nov  4 20:59:53 UTC 2021] Waiting 2, Idle 1, Running 15, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 18
^C
% ./cptac-galaxy/cluster status
...
[Fri Nov  5 01:19:56 UTC 2021] Waiting 0, Idle 0, Running 1, Error 0, Complete 0, Downloaded 17, Skipped 0, Failed 0, Done 17, Total 18
[Fri Nov  5 01:20:56 UTC 2021] Waiting 0, Idle 0, Running 0, Error 0, Complete 0, Downloaded 18, Skipped 0, Failed 0, Done 18, Total 18
[Fri Nov  5 01:20:56 UTC 2021] *** PSM Analysis Complete ***
...
[Fri Nov  5 01:21:14 UTC 2021] *** Summary Reports ***
[Fri Nov  5 01:21:14 UTC 2021] Workflow: Summary Reports: Human, TMT11, Whole Proteome
[Fri Nov  5 01:22:14 UTC 2021] Waiting 1, Idle 0, Running 0, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 1
[Fri Nov  5 01:23:14 UTC 2021] Waiting 0, Idle 1, Running 0, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 1
^C
% ./cptac-galaxy/cluster status
...
[Fri Nov  5 03:22:14 UTC 2021] Waiting 0, Idle 0, Running 0, Error 0, Complete 0, Downloaded 1, Skipped 0, Failed 0, Done 1, Total 1
[Fri Nov  5 03:22:14 UTC 2021] *** Summary Reports Done ***
[Fri Nov  5 03:22:15 UTC 2021] Done.
^C
%
```
3. While the job is running, you can log into the Galaxy instance using the Galaxy Account Email ZZZ@WWW.VVV and the password used to lauch the instance in step 3.1. The URL for accessing the Galaxy instance can either be taken from the output of launch above, the `cptac-galaxy/clusters" command, or the `list` cluster command, which shows running batch jobs. 
```
% ./cptac-galaxy/clusters
CDAP: https://XX.XX.XX.XX
% ./cptac-galaxy/cluster list                                                                  
Cluster CDAP (https://XX.XX.XX.XX) job IDs:
  ExampleStudy_Proteome (running)
%
```
4. The `download` cluster command will download the results of a CDAP job. Note that the download command uses rsync, so will only transfer new or changed files. 
```
% ./cptac-galaxy/cluster download ExampleStudy/Proteome
./cptac-galaxy/cluster download ExampleStudy/Proteome/                                       
receiving incremental file list
./
PSM.tsv/
...
SummaryReports/
...
mzIdentML/
...
mzML/
...

sent 1,524 bytes  received 3,416,903,481 bytes  24,850,218.22 bytes/sec
total size is 3,520,352,957  speedup is 1.03
% 
```
5. Check the downloaded result files to make sure the files have not changed in transit.
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% find mzML -name "*.cksum" -exec ../../cptac-galaxy/cptacdcc/cksum.sh -q {} \;
% find PSM.tsv -name "*.cksum" -exec ../../cptac-galaxy/cptacdcc/cksum.sh -q {} \;
% find mzIdentML -name "*.cksum" -exec ../../cptac-galaxy/cptacdcc/cksum.sh -q {} \;
% cd SummaryReports
%  ../../../cptac-galaxy/cptacdcc/cksum.sh -V -f ExampleStudy_Proteome.cksum .
%
```

## 5. Terminate the CPTAC3 CDAP Galaxy cluster
1. Terminate the cluster using the `cptac-galaxy/terminate` command. 
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/terminate 
Shutdown WinPulsar nodes: new
Shutdown WinPulsar nodes: ok
Shutdown WinPulsar nodes: done
Waiting for AWS cleanup...
Cluster: CDAP
Instances: master (XX.XX.XX.XX) [CPU:18%], winpulsar [CPU:0%]
Other: volume, bucket, stack
Uptime: 21:07:38

Cluster: CDAP
Instances: master (XX.XX.XX.XX) [CPU:18%]
Other: volume, bucket, stack
Uptime: 21:07:55

Cluster: CDAP
Instances: master (XX.XX.XX.XX) [CPU:18%]
Uptime: 21:08:12

Cluster: CDAP
Instances: master (XX.XX.XX.XX) [CPU:18%]
Uptime: 21:08:30

AWS cleanup done.
%
```
2. The `cptac-galaxy/awsresources` command will tell you what AWS resources started by the CPTAC3 CDAP infrastructure are currently running.
```
% ./cptac-galaxy/awsresources
%
```
3. Use the name of the cluster to restrict the information to a specific cluster, and the --delete option to forcibly remove AWS resources associated with that cluster.
```
% ./cptac-galaxy/awsresources CDAP
% ./cptac-galaxy/awsresources CDAP --delete
%
```
