
# CPTAC3 CDAP Execution
Note: These instructions presume a Linux-based x86_64 server, with these instructions developed on CentOS7, with sufficient disk-space to support the various working and result files. 

## Work directory setup
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
4. Configure the CPTAC DCC command-line scripts in `$CPTAC_CDAP_ROOT/cptac-galaxy/cptacdcc`.
```
% cat > cptac-galaxy/cptacdcc/cptacdcc-local.ini
[Portal]
User = UUUUUU
Password = PPPPPPPP
% cptac-galaxy/cptacdcc/cptacdcc CDAP
Folder: /CDAP
InProgress/     2.58 GB   2021-06-25 15:59:00   edwardna
```
## Setup a Study Directory
1. Create working directories for study `ExampleStudy` in `$CPTAC_CDAP_ROOT`.
```
% cd $CPTAC_CDAP_ROOT
% mkdir TutorialStudy
% cd TutorialStudy
% mkdir Proteome
% mkdir Phosphoproteome
```
2. Create and edit the the study parameter file. For CPTAC, valid SPECIES values are "Human", "Human+Mouse" (for CompRef); valid PROTEOME values are "Proteome","Phosphoproteome","Acetylome","Glycoproteome","Ubiquitilome"; valid QUANT values are "iTRAQ", "TMT10", "TMT11"; and valid INST values are "Thermo Q-Exactive HCD" (for all high-accuracy precursor data-dependent acquisitions on Thermo instruments". Some parameters can be omitted for some analysis types. 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cat > ExampleStudy_Proteome.params
SPECIES="Human"
PROTEOME="Proteome"
QUANT="TMT11"
INST="Thermo Q-Exactive HCD"
%
```
3. Create the RAW spectral datafile manifest (depends on placement and data-layout of RAW files on the DCC). 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% ../../cptac-galaxy/dfcoll.sh dcc/UUUUUU PGDAC/6f_non-ccRCC/TMT-DDA-MS | fgrep Proteome > ExampleStudy_Proteome.RAW.txt
%
```
4. Create the tab-separated value isotopic labeling batch correction file (see published studies for examples). Find the necesary values by searcing for the TMT reagent lot numbers at [Thermo Fisher](https://www.thermofisher.com/) and copying from the Certificate of Analysis PDF. For TMT11, two lot numbers are used (TMT10 + TMT11-131C). Note that the label names for TMT10 use 126 and 131, while the label names for TMT11 use 126C, 131N, 131C.  If the labels batch identifiers are not available, use the file `$CPTAC_CDAP_ROOT/cptac-galaxy/Identity_TMT_Label_Correction.txt`
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% cat > ExampleStudy_Proteome.labels.txt
>VA296083_UJ279751      -2      -1      1       2
126C    0.0     0.0     7.4     0.0
127N    0.0     0.0     7.6     0.0
127C    0.0     0.8     6.5     0.0
128N    0.0     0.4     6.6     0.0
128C    0.0     1.5     5.6     0.0
129N    0.0     1.6     5.9     0.0
129C    0.0     2.7     4.7     0.0
130N    0.0     2.4     4.4     0.0
130C    0.0     3.3     3.3     0.0
131N    0.8     2.9     3.7     0.0
131C    0.0     3.8     3.3     0.0
%
```
5. Create the tab-separated values experimental design (sample) file (see published studies for examples). Usually this requires checking the meta-data provided by the data-generators. Headers include: `FileNameRegEx`, `AnalyticalSample`, `LabelReagent`, `Ratios`, and the label names. Values in the LabelRegent column should match one of the batch correction names in the `ExampleStudy_Proteome.labels.txt` file. Label name headers should match the label names in the batch correction label names. Values in the Ratios column should be separated by commas, and use the label names from the batch correction file. 
```
% cd $CPTAC_CDAP_ROOT/ExampleStudy/Proteome
% touch ExampleStudy_Proteome.sample.txt
% 
```
