
# CPTAC3 CDAP Execution

Documentation of the steps to run a CPTAC3 CDAP analysis of a CPTAC3 study. Presumes access to the CPTAC private portal (CPTAC Data Exchange Sandbox), contact cptac.dcc.help@esacinc.com for an account if entitled to access this data. Most of the instructions, however, are generic, with only the location of the RAW spectral datafiles requiring private portal access.

These instructions presume a Linux-based x86_64 machine with sufficient disk-space to support the various working and result files. 

A demonstration dataset ("ExampleStudy") has been created for the purpose of this documentation.

The basic steps are:

1. [Establish a CPTAC3 CDAP working directory](#1-establish-a-cptac3-cdap-working-directory)
2. [Create a CPTAC Study working directory](step2)
3. [Launch a new CPTAC3 CDAP Galaxy cluster on AWS](step3)
4. [Execute the CDAP Analysis](step4)
5. [Terminate the CPTAC3 CDAP Galaxy cluster](step5)

Detailed steps are provided below.

## 1. Establish a CPTAC3 CDAP working directory
1. Establish a working directory. Where necesary, we will specify this working directory as `$CPTAC_CDAP_ROOT`.
2. Download and unpack the CPTAC3 CDAP execution infrastructure.
```
% cd $CPTAC_CDAP_ROOT
% wget -O - -q http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com/cptac-galaxy-setup.sh | sh
```
3. Configure the CPTAC3 CDAP execution infrastructure for AWS.
```
% cd $CPTAC_CDAP_ROOT/cptac-galaxy
% ./configure
AWS Access Key: XXXXXXXXXXXXXXXXXXXX
AWS Secret Key: YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
Galaxy Account Email: ZZZ@WWW.VVV
CPTAC DCC Username (Optional): UUUUUU
CPTAC DCC Password: PPPPPPPP
```
4. Configure the CPTAC DCC command-line scripts in `$CPTAC_CDAP_ROOT/cptac-galaxy/cptacdcc`. Contact the CPTAC DCC to get login details if necessary.
```
% cat > cptac-galaxy/cptacdcc/cptacdcc-local.ini
[Portal]
User = UUUUUU
Password = PPPPPPPP
% cptac-galaxy/cptacdcc/cptacdcc CDAP
Folder: /CDAP
InProgress/     2.58 GB   2021-06-25 15:59:00   edwardna
```
## 2. Create a CPTAC Study working directory
1. Create working directories for study `ExampleStudy` in `$CPTAC_CDAP_ROOT`.
```
% cd $CPTAC_CDAP_ROOT
% mkdir TutorialStudy
% cd TutorialStudy
% mkdir Proteome
% mkdir Phosphoproteome
```
2. Create and edit the the study parameter file. For CPTAC, valid SPECIES values are "Human", "Human+Mouse" (for CPTAC CompRef), "Mouse", "Rat"; valid PROTEOME values are "Proteome","Phosphoproteome","Acetylome","Glycoproteome","Ubiquitilome"; valid QUANT values are "Label-Free", "iTRAQ", "TMT6", "TMT10", "TMT11"; and valid INST values are "Thermo Q-Exactive HCD" (for all high-accuracy precursor data-dependent acquisitions on Thermo instruments). Some parameters can be omitted for some analysis types. For a starting template, see `$CPTAC_CDAP_ROOT/cptac-galaxy/template.params`. 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cat > ExampleStudy_Proteome.params
SPECIES="Human"
PROTEOME="Proteome"
QUANT="TMT11"
INST="Thermo Q-Exactive HCD"
%
```
3. Create the RAW spectral datafile manifest (depends on placement and data-layout of RAW files on the DCC). Other RAW spectral datafile sources are supported, including local files, public URLs, and AWS S3. A full description of these capabilities and the format of the maifest file can be found elsewhere.  
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% ../../cptac-galaxy/dfcoll.sh dcc/UUUUUU PGDAC/... > ExampleStudy_Proteome.RAW.txt
%
```
4. Create the tab-separated value isotopic labeling batch correction file (see published studies for examples). Find the necesary values by searcing for the TMT reagent lot numbers at [Thermo Fisher](https://www.thermofisher.com/) and copying from the Certificate of Analysis PDF. For TMT11, two lot numbers are used (TMT10 + TMT11-131C). Note that the label names for TMT10 use 126 and 131, while the label names for TMT11 use 126C, 131N, 131C.  If the labels batch identifiers are not available use `$CPTAC_CDAP_ROOT/cptac-galaxy/Identity_TMT_Label_Correction.txt` or for a starting template, use the file `$CPTAC_CDAP_ROOT/cptac-galaxy/template.labels.txt`
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cp $CPTAC_CDAP_ROOT/cptac-galaxy/template.labels.txt ExampleStudy_Proteome.labels.txt
%
```
5. Create the tab-separated values experimental design (sample) file (see published studies for examples). Usually this requires checking the meta-data provided by the data-generators. Headers include: `FileNameRegEx`, `AnalyticalSample`, `LabelReagent`, `Ratios`, and the label names. Values in the LabelRegent column should match one of the batch correction names in the `ExampleStudy_Proteome.labels.txt` file. Label name headers should match the label names in the batch correction label names. Values in the Ratios column should be separated by commas, and use the label names from the batch correction file. For a starting template, use the file `$CPTAC_CDAP_ROOT/cptac-galaxy/template-tmt10.sample.txt` or  `$CPTAC_CDAP_ROOT/cptac-galaxy/template-tmt11.sample.txt`
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cp $CPTAC_CDAP_ROOT/cptac-galaxy/template-tmt11.sample.txt ExampleStudy_Proteome.sample.txt
% 
```
6. A completely setup study directory will have `*.params`, `*.RAW.txt`, `*.labels.txt`, and `*.sample.txt` files with a common prefix:
```
% ls -1
ExampleStudy_Proteome.label.txt
ExampleStudy_Proteome.params
ExampleStudy_Proteome.RAW.txt
ExampleStudy_Proteome.sample.txt
```

## 3. Launch a new CPTAC3 CDAP Galaxy cluster on AWS
1. Launch the cluster. NOTE that only one cluster with a given name may be used per AWS account. 
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/launch CLUSTERNAME
Password: AAAAAAAAA
[00:04] Status: pending 
[00:19] IP: 3.231.225.173 Status: booting 
[01:06] IP: 3.231.225.173 Status: running 
...
Setting autoscale, max 2 workers
Indexed sequence databases and auto-scale workers ready.
Windows pulsar nodes will come online shortly.
%
```
## 4. Execute the CDAP Analysis
1. Note that the `*.labels.txt` and `*.samples.txt` files are not required for a mzML RAW file conversion analysis. Use the `cptac-galaxy/cluster` program to manage running batch jobs on the AWS cluster. The `cdap` cluster command starts a CDAP batch job. Use `<ctrl>-C` to escape from the status output. 
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/cluster cdap -a mzML ./ExampleStudy/Proteome/ExampleStudy_Proteome.params
[Fri Oct 29 21:00:31 UTC 2021] *** mzML Analysis ***
[Fri Oct 29 21:00:31 UTC 2021] Workflow: Raw to mzML.gz
[Fri Oct 29 21:01:31 UTC 2021] Waiting 25, Idle 0, Running 0, Error 0, Complete 0, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 25
^C
%
```
2. The `status` cluster command can be used to get the current status of the job.
```
% ./cptac-galaxy/cluster status
...
[Fri Oct 29 21:01:31 UTC 2021] Waiting 10, Idle 0, Running 2, Error 0, Complete 13, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 25
[Fri Oct 29 21:02:31 UTC 2021] Waiting 9, Idle 0, Running 2, Error 0, Complete 14, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 25
[Fri Oct 29 21:03:31 UTC 2021] Waiting 8, Idle 0, Running 2, Error 0, Complete 15, Downloaded 0, Skipped 0, Failed 0, Done 0, Total 25
...
[Fri Oct 29 21:16:31 UTC 2021] Waiting 0, Idle 0, Running 0, Error 0, Complete 0, Downloaded 25, Skipped 0, Failed 0, Done 25, Total 25
[Fri Oct 29 21:16:31 UTC 2021] *** mzML Analysis Complete ***
...
[Fri Oct 29 21:16:49 UTC 2021] Done.
^C
%
```
%
3. The `download` cluster command will download the results of a CDAP job. Note that the download command uses rsync, so will only transfer new or changed files. 
```
% ./cptac-galaxy/cluster download ExampleStudy/Proteome
receiving incremental file list
./
mzML/
...

sent 537 bytes  received 4,158,906,123 bytes  26,405,756.57 bytes/sec
total size is 4,157,736,288  speedup is 1.00
% 
```

## 5. Terminate the CPTAC3 CDAP Galaxy cluster
1. Terminate the cluster
```
% cd $CPTAC_CDAP_ROOT
% ./cptac-galaxy/terminate 
Shutdown WinPulsar nodes: new
Shutdown WinPulsar nodes: ok
Shutdown WinPulsar nodes: done
Waiting for AWS cleanup...
Cluster: CLUSTERNAME
Instances: master (3.231.225.173) [CPU:18%], winpulsar [CPU:0%]
Other: volume, bucket, stack
Uptime: 21:07:38

Cluster: CLUSTERNAME
Instances: master (3.231.225.173) [CPU:18%]
Other: volume, bucket, stack
Uptime: 21:07:55

Cluster: CLUSTERNAME
Instances: master (3.231.225.173) [CPU:18%]
Uptime: 21:08:12

Cluster: CLUSTERNAME
Instances: master (3.231.225.173) [CPU:18%]
Uptime: 21:08:30

AWS cleanup done.
%
```
2. The `awsresources` command will tell you what AWS resources started by the CPTAC3 CDAP infrastructure are currently running.
```
% ./cptac-galaxy/awsresources
%
```
3. Use the name of the cluster to restrict the information to a specific cluster, and the --delete option to forcibly remove AWS resources associated with that cluster.
```
% ./cptac-galaxy/awsresources CLUSTERNAME
% ./cptac-galaxy/awsresources CLUSTERNAME --delete
%
```
