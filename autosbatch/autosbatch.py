"""Main module."""
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from subprocess import PIPE, call, check_output, run
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from jinja2 import Environment, FileSystemLoader
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

logger = logging.getLogger(__name__)

# TODO: Add a logger
# TODO: Add a progress bar
# TODO: submit to nodes sorted by load


class SlurmPool:
    """A class for submitting jobs to Slurm."""

    # TODO: support context manager
    FILE_DIR = './.autosbatch'
    LOG_DIR = f'{FILE_DIR}/log'
    SCRIPTS_DIR = f'{FILE_DIR}/scripts'

    def __init__(
        self,
        pool_size: Optional[int] = None,
        ncpus_per_job: int = 2,
        max_jobs_per_node: Optional[int] = None,
        node_list: Optional[List[str]] = None,
        partition: Optional[str] = None,
        max_pool_size: int = 1000,
    ):
        self.ncpus_per_job = ncpus_per_job  # TODO: change to 1, when hyperthreading is disabled

        self.nodes = self.get_nodes()
        self._get_avail_nodes(node_list=node_list, partition=partition)
        self.node_list = list(self.nodes.keys())
        if len(self.node_list) == 0:
            # TODO: use logging.error
            raise RuntimeError('No Nodes are qualtified.')

        self._set_max_jobs_per_node(max_jobs_per_node=max_jobs_per_node)

        jobs_on_nodes = {k: v['max_jobs'] for k, v in self.nodes.items()}
        self.jobs_on_nodes = {
            k: v if v <= self.max_jobs_per_node else self.max_jobs_per_node for k, v in jobs_on_nodes.items()
        }
        self._set_pool_size(pool_size=pool_size, max_pool_size=max_pool_size)

    @classmethod
    def get_nodes(cls, sortByload=True) -> OrderedDict:
        """Get nodes information from sinfo."""
        # TODO: get rid of pandas
        command = ['sinfo', '-o', '"%n %e %m %a %c %C %O %R %t"']
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        nodes = {}
        for line in result.stdout.splitlines():
            line = line.strip('\"')
            if line.startswith('HOSTNAMES'):
                continue
            node, free_mem, memory, avail, cpus, free_cpus, load, partition, state = line.split()
            nodes[node] = {
                'free_mem': int(free_mem),
                'used_mem': int(memory) - int(free_mem),
                'memory': int(memory),
                'AVAIL': avail,
                'cpus': int(cpus),
                'used_cpus': int(free_cpus.split('/')[0]),
                'free_cpus': int(free_cpus.split('/')[1]),
                'load': float(load),
                'partition': partition,
                'state': state,
            }
        if sortByload:
            nodes = OrderedDict(
                sorted(nodes.items(), key=lambda x: (x[1]['load'], x[1]['used_mem'], x[1]['used_cpus']))
            )
        logger.debug(f'Found {len(nodes)} nodes.')
        return nodes

    def _get_avail_nodes(
        self,
        states: List[str] = ['idle', 'mix'],
        node_list: Optional[List[str]] = None,
        partition: Optional[str] = None,
    ) -> dict:
        """Get available nodes."""
        if node_list:
            self.nodes = {k: self.nodes[k] for k in node_list if k in self.nodes}
        if partition:
            self.nodes = {k: v for k, v in self.nodes.items() if v['partition'] == partition}
        self.nodes = {k: v for k, v in self.nodes.items() if v['state'] in states}
        self.nodes = {k: v for k, v in self.nodes.items() if v['free_cpus'] >= self.ncpus_per_job}

    def _set_max_jobs_per_node(
        self, max_jobs_per_node: Optional[int] = None,
    ):
        """Set max_jobs_per_node."""
        for v in self.nodes.values():
            v['max_jobs'] = v['free_cpus'] // self.ncpus_per_job
        avail_max_jobs_per_node = max(v['max_jobs'] for v in self.nodes.values())
        if max_jobs_per_node:
            if max_jobs_per_node > avail_max_jobs_per_node:
                raise RuntimeError(f'max_jobs_per_node should not be larger than {avail_max_jobs_per_node}')
            else:
                self.max_jobs_per_node = max_jobs_per_node
        else:
            self.max_jobs_per_node = avail_max_jobs_per_node

    def _set_pool_size(
        self, pool_size: Optional[int] = None, max_pool_size: Optional[int] = None,
    ):
        """Set pool_size."""
        max_pool_size = min(sum(self.jobs_on_nodes.values()), max_pool_size)
        if pool_size:
            if pool_size > max_pool_size:
                raise RuntimeError(f'pool_size should not be larger than {max_pool_size}')
            else:
                self.pool_size = pool_size
        else:
            self.pool_size = max_pool_size

    @classmethod
    def single_submit(
        cls,
        partition: str,
        node: str,
        cpus_per_task: int,
        cmds: List[str],
        job_name: str = 'aotusbatch',
        job_id: str = '001',
        logging_level: int = logging.WARNING,
    ):
        # TODO: replace call with subprocess.run
        Path(cls.SCRIPTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_DIR).mkdir(parents=True, exist_ok=True)
        templateLoader = FileSystemLoader(searchpath=f"{os.path.dirname(os.path.realpath(__file__))}/template")
        env = Environment(loader=templateLoader)
        template = env.get_template('CPU_OpenMP.j2')
        output_from_parsed_template = template.render(
            job_name=job_name,
            job_id=job_id,
            partition=partition,
            node=node,
            cpus_per_task=cpus_per_task,
            cmds='\n'.join(cmds),
        )
        with open(f'{cls.SCRIPTS_DIR}/scripts_{job_id}.sh', 'w') as f:
            f.write(output_from_parsed_template)
        time.sleep(1)
        call(f'chmod 755 {cls.SCRIPTS_DIR}/scripts_{job_id}.sh', shell=True)
        slurm_id = check_output(f'sbatch {cls.SCRIPTS_DIR}/scripts_{job_id}.sh', shell=True)
        slurm_id = slurm_id.decode().strip().split()[-1]
        logger.setLevel(logging_level)
        logger.info(f'Queue: {job_name}_{job_id}, Job ID: {slurm_id}, Node: {node}, N_jobs: {len(cmds)}')

    def multi_submit(self, cmds: List[str], n_jobs: int, job_name: str, logging_level: int = logging.WARNING):
        # TODO: support shuffling
        cmd_bin = [[] for _ in range(min(n_jobs, self.pool_size))]
        for i, cmd in enumerate(cmds, start=1):
            cmd_bin[i % self.pool_size - 1].append(cmd)
        ith = 0
        for node, n_jobs in self.jobs_on_nodes.items():
            for _ in range(n_jobs):
                self.single_submit(
                    self.nodes[node]['partition'],
                    node,
                    self.ncpus_per_job,
                    cmd_bin[ith],
                    job_name,
                    f'{ith:>03}',
                    logging_level,
                )
                ith += 1
                if ith >= len(cmd_bin):
                    break
            else:
                continue
            break

    def starmap(self, func: Callable, params: Iterable[Iterable]):
        """
        func: function
        params: list of tuple
        return: None
        """
        cmds = [func(*i) for i in params]
        self.multi_submit(cmds, len(params), func.__name__)

    def map(self, func: Callable, params: Iterable):
        """
        func: function
        params: list
        return: None
        """
        cmds = [func(i) for i in params]
        self.multi_submit(cmds, len(params), func.__name__)

    @classmethod
    def clean(cls):
        """Clean up the scripts and log files"""
        command = ['rm', '-rf', cls.FILE_DIR]
        _ = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
