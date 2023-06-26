"""Main module."""
import datetime
import json
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from subprocess import PIPE, run
from typing import Callable, Dict, Iterable, List, Optional, Union

from jinja2 import Environment, FileSystemLoader
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn

# from autosbatch.logger import logger



class SlurmPool:
    """A class for submitting jobs to Slurm."""

    dir_path = '.autosbatch'

    CPU_OpenMP_TEMPLATE = 'CPU_OpenMP.j2'

    def __init__(
        self,
        pool_size: Optional[int] = None,
        ncpus_per_job: int = 1,
        max_jobs_per_node: Optional[int] = None,
        node_list: Optional[List[str]] = None,
        partition: Optional[str] = None,
        max_pool_size: int = 1000,
    ):
        """
        Initialize a SlurmPool object.

        Parameters
        ----------
        pool_size : int, optional
            Number of jobs to submit at the same time, by default None
        ncpus_per_job : int, optional
            Number of cpus per job, by default 1
        max_jobs_per_node : int, optional
            Maximum number of jobs to submit to a single node, by default None
        node_list : List[str], optional
            List of nodes to submit jobs to, by default None
        partition : str, optional
            Partition to submit jobs to, by default None
        max_pool_size : int, optional
            Maximum number of jobs to submit, by default 1000
        """
        self.ncpus_per_job = ncpus_per_job
        self.logger = logging.getLogger('autosbatch')
        self.nodes = self.get_nodes()
        self._get_avail_nodes(node_list=node_list, partition=partition)
        self.node_list = list(self.nodes.keys())
        if len(self.node_list) == 0:
            raise RuntimeError('No Nodes are qualtified.')

        self._set_max_jobs_per_node(max_jobs_per_node=max_jobs_per_node)

        jobs_on_nodes = {k: v['max_jobs'] for k, v in self.nodes.items()}
        self.jobs_on_nodes = {
            k: v if v <= self.max_jobs_per_node else self.max_jobs_per_node for k, v in jobs_on_nodes.items()
        }
        self._set_pool_size(pool_size=pool_size, max_pool_size=max_pool_size)
        self.time_now = datetime.datetime.now().strftime('%m%d%H%M%S')
        self.file_dir = f'{self.dir_path}/{self.time_now}'
        self.log_dir = f'{self.file_dir}/log'
        self.scripts_dir = f'{self.file_dir}/scripts'

    @classmethod
    def get_nodes(cls, sortByload=True) -> Dict:
        """
        Get nodes information from sinfo.

        Parameters
        ----------
        sortByload : bool, optional
            Sort nodes by load, by default True

        Returns
        -------
        Dict
            Information of nodes, by default
        """
        command = ['sinfo', '-o', '"%n %e %m %a %c %C %O %R %t"']
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        nodes = {}
        for line in result.stdout.splitlines():
            line = line.strip('\"')
            if line.startswith('HOSTNAMES'):
                continue
            node, free_mem, memory, avail, cpus, free_cpus, load, partition, state = line.split()
            free_mem = int(free_mem) if free_mem != 'N/A' else 0
            memory = int(memory) if memory != 'N/A' else 0
            load = float(load) if load != 'N/A' else 0
            nodes[node] = {
                'free_mem': free_mem,
                'used_mem': memory - free_mem,
                'memory': memory,
                'AVAIL': avail,
                'cpus': int(cpus),
                'used_cpus': int(free_cpus.split('/')[0]),
                'free_cpus': int(free_cpus.split('/')[1]),
                'load': load,
                'partition': partition,
                'state': state,
            }
        if sortByload:
            nodes = dict(
                OrderedDict(sorted(nodes.items(), key=lambda x: (x[1]['load'], x[1]['used_mem'], x[1]['used_cpus'])))
            )
        return nodes

    def _check_hypertreading(self, node_name) -> bool:
        """
        Check if hyperthreading is enabled.

        Parameters
        ----------
        node_name : str
            Name of the node

        Returns
        -------
        bool
            True if hyperthreading is enabled, False otherwise
        """
        command = ['scontrol', 'show', 'node', node_name]
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        if 'ThreadsPerCore=2' in result.stdout:
            return True
        else:
            return False

    def _get_avail_nodes(
        self,
        states: List[str] = ['idle', 'mix'],
        node_list: Optional[List[str]] = None,
        partition: Optional[str] = None,
    ) -> None:
        """
        Get available nodes.

        Parameters
        ----------
        states : List[str], optional
            List of states of nodes, by default ['idle', 'mix']
        node_list : List[str], optional
            List of nodes to submit jobs to, by default None
        partition : str, optional
            Partition to submit jobs to, by default None

        Returns
        -------
        None
        """
        if node_list:
            self.nodes = {k: self.nodes[k] for k in node_list if k in self.nodes}
        if partition:
            self.nodes = {k: v for k, v in self.nodes.items() if v['partition'] == partition}
        self.nodes = {k: v for k, v in self.nodes.items() if v['state'] in states}
        self.nodes = {k: v for k, v in self.nodes.items() if v['free_cpus'] >= self.ncpus_per_job}

    def _set_max_jobs_per_node(
        self, max_jobs_per_node: Optional[int] = None,
    ):
        """
        Set max_jobs_per_node.

        Parameters
        ----------
        max_jobs_per_node : int, optional
            Maximum number of jobs to submit to a single node, by default None

        Returns
        -------
        None
        """
        if self.ncpus_per_job & 0x1:
            for node in self.nodes.keys():
                if self._check_hypertreading(node):
                    self.ncpus_per_job += 1
                    self.logger.warning(
                        f'Hyperthreading is enabled on {node}, ncpus_per_job is set to {self.ncpus_per_job}.'
                    )
                    break
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
        self, max_pool_size: int, pool_size: Optional[int] = None,
    ):
        """
        Set pool_size.

        Parameters
        ----------
        max_pool_size : int
            Maximum number of jobs to submit
        pool_size : int, optional
            Number of jobs to submit, by default None

        Returns
        -------
        None
        """
        max_pool_size = min(sum(self.jobs_on_nodes.values()), max_pool_size)
        if pool_size:
            if pool_size > max_pool_size:
                raise RuntimeError(f'pool_size should not be larger than {max_pool_size}')
            else:
                self.pool_size = pool_size
        else:
            self.pool_size = max_pool_size

    def single_submit(
        self,
        partition: str,
        node: str,
        cpus_per_task: int,
        cmds: Union[str, List[str]],
        job_name: str = 'job',
        # logging_level: int = logging.WARNING,
    ):
        """
        Submit a single job.

        Parameters
        ----------
        partition : str
            Partition to submit jobs to
        node : str
            Node to submit jobs to
        cpus_per_task : int
            Number of CPUs to use
        cmds : str or List[str]
            Commands to run
        job_name : str, optional
            Name of the job, by default 'job'
        logging_level : int, optional
            Logging level, by default logging.WARNING

        Returns
        -------
        None
        """
        # self.logger.setLevel(logging_level)
        Path(self.scripts_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        templateLoader = FileSystemLoader(searchpath=f"{os.path.dirname(os.path.realpath(__file__))}/template")
        env = Environment(loader=templateLoader)
        template = env.get_template(self.CPU_OpenMP_TEMPLATE)

        if isinstance(cmds, str):
            cmds = [cmds]
        output_from_parsed_template = template.render(
            job_name=job_name,
            partition=partition,
            node=node,
            cpus_per_task=cpus_per_task,
            cmds='\n'.join(cmds),
            log_dir=self.log_dir,
        )
        script_path = f'{self.scripts_dir}/{job_name}.sh'
        with open(script_path, 'w') as f:
            f.write(output_from_parsed_template)
        command = ['chmod', '755', script_path]
        _ = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        command = ['sbatch', script_path]
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        slurm_id = result.stdout.strip().split()[-1]
        self.logger.info(f'Sumbitted Task: {job_name} to {node}, containing {len(cmds)} jobs. Slurm ID: {slurm_id}')
        self.logger.debug(f'Commands: {cmds}')

    def multi_submit(
        self,
        cmds: List[str],
        job_name: str,
        # logging_level: int = logging.WARNING,
        shuffle: bool = False,
        sleep_time: float = 0.5,
    ):
        """
        Submit jobs to multiple nodes.

        Parameters
        ----------
        cmds : List[str]
            Commands to run
        job_name : str
            Name of the job
        logging_level : int, optional
            Logging level, by default logging.WARNING
        shuffle : bool, optional
            Shuffle the commands, by default False
        sleep_time : float, optional
            Time to sleep between each submission, by default 0.5

        Returns
        -------
        None
        """
        if shuffle:
            import random

            random.shuffle(cmds)
        # self.logger.setLevel(logging_level)
        self.logger.info(f'Found {len(self.nodes)} available nodes.')
        self.pool_size = min(self.pool_size, len(cmds))
        self.logger.info(f'{len(cmds):,} jobs to excute, allocated to {self.pool_size} tasks.')
        self.logger.info(f'Each task will use {self.ncpus_per_job} cpus.')

        used_nodes = {}
        registed_jobs = 0
        for k, v in self.jobs_on_nodes.items():
            used_nodes[k] = v
            registed_jobs += v
            if registed_jobs < self.pool_size:
                continue
            elif registed_jobs == self.pool_size:
                break
            else:
                used_nodes[k] -= registed_jobs - self.pool_size
                break
        self.logger.info(f'Used {len(used_nodes)} nodes.')
        self.logger.info(f'Each node will excute {max(used_nodes.values())} tasks in parallel.')
        self.logger.info(f'{used_nodes}')
        k, m = divmod(len(cmds), self.pool_size)
        ith = 0
        task_log = {}
        with Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            auto_refresh=False,
        ) as progress:
            for node, n_jobs in used_nodes.items():
                self.logger.info(f'{node}: {n_jobs} tasks')
                task = progress.add_task(f"Submitting to {node}...", total=n_jobs)
                for _ in range(n_jobs):
                    time.sleep(sleep_time)
                    start, end = ith * k + min(ith, m), (ith + 1) * k + min(ith + 1, m)
                    self.logger.info(f'Task {ith}: containing job {start}-{end-1}')
                    task_name = f'{job_name}_{ith:>03}'
                    self.single_submit(
                        self.nodes[node]['partition'],
                        node,
                        self.ncpus_per_job,
                        cmds[start:end],
                        task_name,
                        # logging_level,
                    )
                    progress.update(task, advance=1)
                    progress.refresh()
                    ith += 1
                    task_log[task_name] = {
                        'node': node,
                        'script': f'{task_name}.sh',
                        'stdout': f'{task_name}.out.log',
                        'stderr': f'{task_name}.err.log',
                        'cmd': cmds[start:end],
                    }
        with open(f'{self.file_dir}/{self.time_now}.log', 'w') as f:
            self.logger.info(f'Writing task log to {self.file_dir}/{self.time_now}.log')
            json.dump(task_log, f, indent=4)

    def starmap(self, func: Callable, params: Iterable[Iterable]):
        """
        Submit a list of commands to the cluster.

        Parameters
        ----------
        func : Callable
            Function to call
        params : Iterable[Iterable]
            Parameters to pass to the function

        Returns
        -------
        None
        """
        cmds = [func(*i) for i in params]
        self.multi_submit(cmds, func.__name__)

    def map(self, func: Callable, params: Iterable):
        """
        Submit a list of commands to the cluster.

        Parameters
        ----------
        func : Callable
            Function to call
        params : Iterable
            Parameters to pass to the function

        Returns
        -------
        None
        """
        cmds = [func(i) for i in params]
        self.multi_submit(cmds, func.__name__)

    @classmethod
    def clean(cls):
        """Clean up the scripts and log files."""
        command = ['rm', '-rf', cls.dir_path]
        _ = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    def close(self):
        """Clean up the scripts and log files."""
        pass

    def __enter__(self):
        """Clean up the scripts and log files."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the scripts and log files."""
        self.close()
