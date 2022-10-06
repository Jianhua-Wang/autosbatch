# autosbatch

Sometimes, it's quite inconvenient when we submit hundreds of jobs to slurm. For example, one needs to align RNA-seq data from one hundred samples. He may start with a bash script that takes the fastq of one sample and write sbatch scripts which execute `bash align.sh sample.fq` multiple times. If he wants to run 50 samples at the same time, he should write 50 sbatch scripts and each script contains two align commands. Manually managing these sbatch scripts is inconvenient. autosbatch is very helpful for submitting slurm jobs automatically and it's just like the `multiprocessing.Pool`.

## Install

```bash
git clone https://github.com:Jianhua-Wang/autosbatch.git
cd autosbatch
pip install .
```

## Usage

example command of job:

```python
def run_cmd(num, time):
    cmd = f'echo {num} && sleep {time}'
    return cmd
```

parameter list:

```python
params = []
for num in range(5):
    for time in range(6):
        params.append([num, time])
```

submit to slurm, run 10 job at the same time.

```python
from autosbatch import SlurmPool

p = SlurmPool(10)
p.starmap(run_cmd, params)
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
for example:
```python
p = SlurmPool(  pool_size=100,
                ncpus_per_job=2,
                max_jobs_per_node=20,
                node_list=['cpu01','cpu02','cpu03']
                )
```

submit single job:

```python
SlurmPool.autosbatch(partition='cpuPartition',
                    node='cpu01',
                    cpus_per_task=1,
                    cmds='sleep 10',
                    job_name='test',
                    job_id='001')

```
