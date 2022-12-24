# autosbatch


[![pypi](https://img.shields.io/pypi/v/autosbatch.svg)](https://pypi.org/project/autosbatch/)
[![python](https://img.shields.io/pypi/pyversions/autosbatch.svg)](https://pypi.org/project/autosbatch/)
[![Build Status](https://github.com/Jianhua-Wang/autosbatch/actions/workflows/dev.yml/badge.svg)](https://github.com/Jianhua-Wang/autosbatch/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/Jianhua-Wang/autosbatch/branch/main/graphs/badge.svg)](https://codecov.io/github/Jianhua-Wang/autosbatch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI download month](https://img.shields.io/pypi/dm/autosbatch.svg)](https://pypi.org/project/autosbatch/)


submit hundreds of jobs to slurm automatically


* Documentation: <https://Jianhua-Wang.github.io/autosbatch>
* GitHub: <https://github.com/Jianhua-Wang/autosbatch>
* PyPI: <https://pypi.org/project/autosbatch/>
* Free software: MIT


## Features

Sometimes, it's quite inconvenient when we submit hundreds of jobs to slurm. For example, one needs to align RNA-seq data from one hundred samples. He may start with a bash script that takes the fastq of one sample and write sbatch scripts which execute `bash align.sh sample.fq` multiple times. If he wants to run 50 samples at the same time, he should write 50 sbatch scripts and each script contains two align commands. Manually managing these sbatch scripts is inconvenient. autosbatch is very helpful for submitting slurm jobs automatically and it's just like the `multiprocessing.Pool`.

* Automatically submit hundreds of jobs to Slurm with a few code.
* The same usage as `multiprocessing.Pool`.
* Provide command line tool for people who are not familiar with Python.

## TODO

* Support gpu allocation
* Support MPI jobs

## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [waynerv/cookiecutter-pypackage](https://github.com/waynerv/cookiecutter-pypackage) project template.
