# CPTAC3 CDAP: cluster

The `cluster` command is used to manage batch execution jobs on the CPTAC3 CDAP cluster. It can upload files and data needed for execution of batch jobs, initiate a CDAP analysis batch job, start and stop batch jobs, display job status and logfiles, and remove all remnants of a batch job. The command can be used to manage batch jobs for multiple  CPTAC3 CDAP Galaxy clusters and to manage mutliple jobs per cluster. If there is a single cluster and a single job, these need not be specified in most cases.

## Cluster Commands

### cdap

The cluster cdap command initiates a CPTAC3 CDAP analysis based on the information in a `.params` file (and other associated files) in a study directory.

Usage: `cptac-galaxy/cluster [ <CLUSTERNAME> ] cdap [ -a <ANALYSIS> ] <PARAMSFILE>`

where `<ANALYSIS>` is one of "mzML", "PSM", "Reports", "Complete"; and `<PARAMSFILE>` is the path to the `.params` file in a study directory. A Complete analysis consists of the PSM analysis followed by the Reports analysis. The Complete analysis is carried out if no `-a` option is specified. mzML RAW spectral file conversion is carried out by the mzML analysis and as part of the PSM analysis. The name of the batch jobs on the cluster is taken from the `.params` filename. 

Examples:
* Run the complete CDAP analysis on the Proteome data from the ExampleStudy study.
```
% cptac-galaxy/cluster cdap ExampleStudy/Proteome/ExampleStudy_Proteome.params
```
* Run the CDAP to create mzML spectral datafiles for the Proteome data from the ExampleStudy study.
```
% cptac-galaxy/cluster cdap -a mzML ExampleStudy/Proteome/ExampleStudy_Proteome.params
```

### list

The cluster list command shows the job ids of jobs submitted to the cluster and whether they are running or not.

Usage: `cptac-galaxy/cluster [ <CLUSTERNAME> ] list`

Examples:
* List the job ids of jobs submitted to the cluster.
```
% cptac-galaxy/cluster list
```

### status

The cluster status command shows the tail of a batch job's primary execution logfile. This is the primary method for observing the progress of the batch job.

Usage: `cptac-galaxy/cluster [ <CLUSTERNAME> ] status [ <JOBID> ] [ all ]`

If no `<JOBID>` is provided, provide status for all jobs running on the cluster, and if the `all` argument is provided, show all logfiles (not just the primary execution logfile) for all jobs running on the cluster. If `<JOBID>` is provided, show the primary execution logfile for the specific job, and if the `all` argument is provided show all logfiles for the specific job. 

Examples:
* Get the status of all jobs on the cluster.
```
% cptac-galaxy/cluster status 
```






