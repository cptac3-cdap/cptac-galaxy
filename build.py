from cx_Freeze import setup, Executable

base = 'Console'

executables = [
    Executable('configure.py', base=base),
    Executable('launch.py', base=base),
    Executable('execute.py', base=base),
    Executable('terminate.py', base=base),
    Executable('clusters.py', base=base),
    Executable('wfupload.py', base=base),
    Executable('wfdownload.py', base=base),
    Executable('dsdownload.py', base=base),
    Executable('login.py', base=base),
    Executable('awsresources.py', base=base),
    Executable('dfcollection.py', base=base),
    Executable('cluster.py', base=base),
    Executable('fixqcmetrics.py', base=base),
]

includes = [
    'seqdb',
    'workflows',
    'data',
    'cptacdcc',
    'update.sh',
    'organize0.sh',
    'organize1.sh',
    'organize1all.sh',
    'execute_report.sh',
    'dfcoll.sh',
    'VERSION',
    '.defaults.ini'
]

buildOptions = dict(packages = [], excludes = [], includes = [], 
		    include_files = includes)

setup(name='CPTAC-Galaxy',
      version = open('VERSION').read(),
      description = '',
      options = dict(build_exe = buildOptions),
      executables = executables)
