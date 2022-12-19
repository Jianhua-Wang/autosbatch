# Usage

## Usage for package

### Import

```Python
import autosbatch
# or import SlurmPool directly
from autosbatch import SlurmPool
```

### submit single job
run `sleep 10` on node `cpu01` on `cpuPartition` paritition.
```Python
SlurmPool.single_submit(partition='cpuPartition',
                        node='cpu01',
                        cpus_per_task=1,
                        cmds='sleep 10',
                        job_name='test',
                        job_id='001')

```

or run a job containing two steps, e.g. `echo hello` and `sleep 10`
```Python
SlurmPool.single_submit(partition='cpuPartition',
                        node='cpu01',
                        cpus_per_task=1,
                        cmds=['echo hello','sleep 10'],
                        job_name='test',
                        job_id='001')

```

### submit multiple job
TODO: compare multiprocessing.Pool.map
TODO: add with syntax

Just like `multiprocessing.Pool.map`
```python
# construct the excutor
def sleep(time):
    cmd = f'sleep {time}'
    return cmd

# prepare the param for each excutor
params = range(10)

# submit to parallel run
p = SlurmPool(10)
p.map(sleep, params)
```

multiple parameters (similar with `multiprocessing.Pool.starmap`)

```Python
# construct the excutor
def echo_sleep(text, time):
    cmd = f'echo {text} && sleep {time}'
    return cmd

# prepare the params for each excutor
params = []
for text in range(5):
    for time in range(6):
        params.append([text, time])

# submit to parallel run
p = SlurmPool(10)
p.starmap(echo_sleep, params)
```

The sbatch scripts are put in `./autosbatch/$timenow/script`. The error and stdout logs are in `./autosbatch/$timenow/log`.

remove `script` dir:

```Python
SlurmPool.clean()
```

Custom the job Pool:
```Python
p = SlurmPool(  pool_size=None, #how many jobs run in parallel, use all resources if not specify.
                ncpus_per_job=2, #how many cpus per job use
                max_jobs_per_node=None, #how many jobs can a node run at most
                node_list=None # use all nodes if not specify
                )
```

## Usage for CLI tool

### help message
```Bash
$ autosbatch --help

 Usage: autosbatch [OPTIONS] COMMAND [ARGS]...

 Submit jobs to slurm cluster, without writing slurm script files.

╭─ Options ───────────────────────────────────────────────────────────────────────╮
│ --version  -V        Show version.                                              │
│ --verbose  -v        Show verbose info.                                         │
│ --dev                Show dev info.                                             │
│ --help     -h        Show this message and exit.                                │
╰─────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────╮
│ clean              Remove all scripts and logs.                                 │
│ multi-job          Submit multiple jobs to slurm cluster.                       │
│ single-job         Submit a single job to slurm cluster.                        │
╰─────────────────────────────────────────────────────────────────────────────────╯
```
### Command: single-job
```Bash
$ autosbatch single-job -h
─────────────────────────────────── AutoSbatch ────────────────────────────────────

 Usage: autosbatch single-job [OPTIONS] CMD...

 Submit a single job to slurm cluster.

╭─ Arguments ─────────────────────────────────────────────────────────────────────╮
│ *    cmd      CMD...  Command to run. [default: None] [required]                │
╰─────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────╮
│ --ncpus      -n      INTEGER  Number of cpus. [default: 1]                      │
│ --node       -N      TEXT     Node to submit job to. [default: None]            │
│ --partition  -P      TEXT     Partition to submit jobs to. [default: None]      │
│ --job-name   -j      TEXT     Name of the job. [default: job]                   │
│ --help       -h               Show this message and exit.                       │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

run example command such as `sleep 10`
```Bash
autosbatch single-job sleep 10
─────────────────────────────────── AutoSbatch ────────────────────────────────────
[22:13:46] WARNING  Hyperthreading is enabled on cpu14, ncpus_per_job is set to 2.
```

### Command: multi-job
```Bash
$ autosbatch multi-job -h
─────────────────────────────────── AutoSbatch ────────────────────────────────────

 Usage: autosbatch multi-job [OPTIONS] CMDFILE

 Submit multiple jobs to slurm cluster.

╭─ Arguments ─────────────────────────────────────────────────────────────────────╮
│ *    cmdfile      PATH  Path to the command file. [default: None] [required]    │
╰─────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────╮
│ --pool-size          -p      INTEGER RANGE             Number of jobs to submit │
│                              [0<=x<=1000]              at the same time.        │
│                                                        [default: None]          │
│ --ncpus-per-job      -n      INTEGER                   Number of cpus per job.  │
│                                                        [default: 1]             │
│ --max-jobs-per-node  -m      INTEGER                   Maximum number of jobs   │
│                                                        to submit to a single    │
│                                                        node.                    │
│                                                        [default: None]          │
│ --node-list          -l      TEXT                      List of nodes to submit  │
│                                                        jobs to. e.g. "-l node1  │
│                                                        -l node2 -l node3"       │
│                                                        [default: None]          │
│ --partition          -P      TEXT                      Partition to submit jobs │
│                                                        to.                      │
│                                                        [default: None]          │
│ --job-name           -j      TEXT                      Name of the job.         │
│                                                        [default: job]           │
│ --help               -h                                Show this message and    │
│                                                        exit.                    │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

submit 10 commands to slurm

Step1. write the commands into a text file, one command per line.
```Bash
$ cat ./cmd.sh
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

Step2 run `multi-job` command
```Bash
$ autosbatch multi-job --max-jobs-per-node 3 -P gpu -l gpu02 -l gpu03 ./cmd.sh
────────────────────────────────── AutoSbatch ──────────────────────────────────
Submitting to gpu02... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3 0:00:00
Submitting to gpu03... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3 0:00:00
```

### Command: clean
remove the directory contains scripts and logs
```
autosbatch clean
```

### enable `verbose`

add `-v` or `--verbose` between `autosbatch` and `command`

e.g.:
```Bash
$ autosbatch -v multi-job --max-jobs-per-node 3 -P gpu -l gpu02 -l gpu03 ./cmd.sh
────────────────────────────────── AutoSbatch ──────────────────────────────────
[22:21:44] INFO     Verbose mode is on.
           INFO     Found 2 available nodes.
           INFO     10 jobs to excute, allocated to 6 tasks.
           INFO     Each task will use 1 cpus.
           INFO     Used 2 nodes.
           INFO     Each node will excute 3 tasks in parallel.
           INFO     {'gpu02': 3, 'gpu03': 3}
           INFO     gpu02: 3 tasks
           INFO     Task 0: containing job 0-1
           INFO     Sumbitted Task: job_000 to gpu02, containing 2 jobs. Slurm ID: 254554
[22:21:45] INFO     Task 1: containing job 2-3
           INFO     Sumbitted Task: job_001 to gpu02, containing 2 jobs. Slurm ID: 254555
           INFO     Task 2: containing job 4-5
[22:21:46] INFO     Sumbitted Task: job_002 to gpu02, containing 2 jobs. Slurm ID: 254556
           INFO     gpu03: 3 tasks
           INFO     Task 3: containing job 6-7
           INFO     Sumbitted Task: job_003 to gpu03, containing 2 jobs. Slurm ID: 254557
[22:21:47] INFO     Task 4: containing job 8-8
           INFO     Sumbitted Task: job_004 to gpu03, containing 1 jobs. Slurm ID: 254558
           INFO     Task 5: containing job 9-9
           INFO     Sumbitted Task: job_005 to gpu03, containing 1 jobs. Slurm ID: 254559
Submitting to gpu02... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3 0:00:00
Submitting to gpu03... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3 0:00:00
           INFO     Writing task log to .autosbatch/1219222144/1219222144.log
```