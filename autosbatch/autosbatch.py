import random
from io import StringIO
from subprocess import call, check_output
from textwrap import dedent
import logging
import pandas as pd


class SlurmPool:
    script_tail = '''
    wait
    ##############################

    echo "========================================"
    echo "Process end at : "
    date
    '''

    def __init__(
        self, pool_size=None, ncpus_per_job=2, max_jobs_per_node=None, node_list=None
    ):
        self.ncpus_per_job = ncpus_per_job

        self.nodes = self.get_nodes()
        if node_list:
            self.nodes = self.nodes[self.nodes.index.isin(node_list)]
        self.nodes = self.nodes[self.nodes['FREE_CPUS'] // self.ncpus_per_job > 0]
        self.node_list = list(self.nodes.index)
        if len(self.node_list) == 0:
            raise RuntimeError('No Nodes are qualtified.')

        acceptable_max_jobs_per_node = (
            self.nodes['FREE_CPUS'].max() // self.ncpus_per_job
        )
        if max_jobs_per_node:
            if max_jobs_per_node > acceptable_max_jobs_per_node:
                raise RuntimeError(
                    f'max_jobs_per_node should not be larger than {acceptable_max_jobs_per_node}'
                )
            else:
                self.max_jobs_per_node = max_jobs_per_node
        else:
            self.max_jobs_per_node = acceptable_max_jobs_per_node

        jobs_on_nodes = self.nodes['FREE_CPUS'] // self.ncpus_per_job
        self.jobs_on_nodes = jobs_on_nodes.where(
            jobs_on_nodes <= self.max_jobs_per_node, self.max_jobs_per_node
        )
        max_pool_size = sum(self.jobs_on_nodes)

        if pool_size:
            if pool_size > max_pool_size:
                raise RuntimeError(
                    f'pool_size should not be larger than {max_pool_size}'
                )
            else:
                self.pool_size = pool_size
        else:
            self.pool_size = max_pool_size

    @classmethod
    def get_nodes(cls):
        nodes = check_output('sinfo -o "%n %e %m %a %c %C %O %R %t"', shell=True)
        nodes = pd.read_csv(StringIO(nodes.decode()), sep=' ', index_col=0)
        nodes['FREE_CPUS'] = (
            nodes['CPUS(A/I/O/T)'].str.split('/', expand=True)[1].astype(int)
        )
        return nodes

    @classmethod
    def single_submit(
        cls, partition, node, cpus_per_task, cmds, job_name='test', job_id='001'
    ):
        script_head = f'''\
        #!/bin/bash
        #SBATCH --job-name={job_name}_{job_id}
        #SBATCH --partition={partition}
        #SBATCH --nodes=1
        #SBATCH -w {node}
        #SBATCH --cpus-per-task={cpus_per_task}
        #SBATCH --error=./script/log/%j.err.log
        #SBATCH --output=./script/log/%j.out.log

        echo "Process will start at : "
        date
        echo "----------------------------------------"

        ##############################
        '''
        call('mkdir -p ./script/log', shell=True)
        with open(f'./script/scripts_{job_id}.sh', 'w') as f:
            f.write(dedent(script_head))
            f.write(cmds)
            f.write(dedent(cls.script_tail))
        call(f'chmod 755 ./script/scripts_{job_id}.sh', shell=True)
        call(f'sbatch ./script/scripts_{job_id}.sh', shell=True)

    def multi_submit(cls, cmds, n_jobs, job_name, logging_level=logging.ERROR):
        logging.basicConfig(level=logging_level, format='%(message)s')
        cmd_bin = [[] for _ in range(min(n_jobs, cls.pool_size))]
        for i, cmd in enumerate(cmds, start=1):
            cmd_bin[i % cls.pool_size - 1].append(cmd)
        ith = 0
        for node, n_jobs in cls.jobs_on_nodes.items():
            for _ in range(n_jobs):
                logging.info(f'Queue: {ith:>03}, Node: {node}, N_jobs: {len(cmd_bin[ith])}')
                cls.single_submit(
                    cls.nodes.loc[node, 'PARTITION'],
                    node,
                    cls.ncpus_per_job,
                    '\n'.join(cmd_bin[ith]),
                    job_name,
                    f'{ith:>03}',
                )
                ith += 1
                if ith >= len(cmd_bin):
                    break
            else:
                continue
            break

    def starmap(self, func, params):
        cmds = [func(*i) for i in params]
        self.multi_submit(cmds, len(params), func.__name__)

    def map(self, func, params):
        cmds = [func(i) for i in params]
        self.multi_submit(cmds, len(params), func.__name__)

    @classmethod
    def clean(cls):
        call('rm -rf ./script', shell=True)
