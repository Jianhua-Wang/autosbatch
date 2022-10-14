# autosbatch

Sometimes, it's quite inconvenient when we submit hundreds of jobs to slurm. For example, one needs to align RNA-seq data from one hundred samples. He may start with a bash script that takes the fastq of one sample and write sbatch scripts which execute `bash align.sh sample.fq` multiple times. If he wants to run 50 samples at the same time, he should write 50 sbatch scripts and each script contains two align commands. Manually managing these sbatch scripts is inconvenient. autosbatch is very helpful for submitting slurm jobs automatically and it's just like the `multiprocessing.Pool`.

## Install

```bash
git clone https://github.com:Jianhua-Wang/autosbatch.git
cd autosbatch
pip install .
```

## Usage

### import
```python
from autosbatch import SlurmPool
```

### submit single job

```python
SlurmPool.single_submit(partition='cpuPartition',
                        node='cpu01',
                        cpus_per_task=1,
                        cmds='sleep 10',
                        job_name='test',
                        job_id='001')

```

### submit multiple job

single parameter (similar with `multiprocessing.Pool.map`)

```python
def sleep(time):
    cmd = f'sleep {time}'
    return cmd

params = range(10)

p = SlurmPool(10)
p.map(sleep, params)
```

multiple parameters (similar with `multiprocessing.Pool.starmap`)

```python
params = []
for text in range(5):
    for time in range(6):
        params.append([text, time])

def echo_sleep(text, time):
    cmd = f'echo {text} && sleep {time}'
    return cmd

p = SlurmPool(10)
p.starmap(echo_sleep, params)
```

The sbatch scripts are put in `./script`. The error and stdout logs are in `./script/log`.

remove `script` dir:

```python
SlurmPool.clean()
```

Custom the job Pool:

```python
p = SlurmPool(  pool_size=None, #how many jobs run in parallel, use all resources if not specify.
                ncpus_per_job=2, #how many cpus per job use
                max_jobs_per_node=None, #how many jobs can a node run at most
                node_list=None # use all nodes if not specify
                )
```

### Use command line

```bash
$ autosbatch cmd.sh -j test
```

```bash
$ cat cmd.sh
sleep 0
sleep 1
sleep 2
sleep 3
sleep 4
sleep 5
sleep 6
sleep 7
sleep 8
sleep 9

```

help message:

```
$ autosbatch --help                                                   
Usage: autosbatch [OPTIONS] CMDFILE

  autosbatch --ncpus-per-job 10 cmd.sh

Options:
  -p, --pool-size INTEGER         How many jobs do you want to run in
                                  parallel. Use all resources if None.
  -n, --ncpus-per-job INTEGER     How many cpus per job uses, default=2
  -M, --max-jobs-per-node INTEGER
                                  how many jobs can a node run in parallel at
                                  most
  -N, --node-list TEXT            specify the nodes you want to use, separated
                                  by commas, e.g. 'cpu01,cpu02,cpu03', use as
                                  many as you can if None
  -j, --job-name TEXT             job name prefix, default=test
  --help                          Show this message and exit.
```