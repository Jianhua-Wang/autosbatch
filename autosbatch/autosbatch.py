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

from autosbatch.logger import logger


class SlurmPool:
    """A class for submitting jobs to Slurm."""

    time_now = datetime.datetime.now().strftime('%m%d%H%M%S')
    dir_path = '.autosbatch'
    FILE_DIR = f'{dir_path}/{time_now}'
    LOG_DIR = f'{FILE_DIR}/log'
    SCRIPTS_DIR = f'{FILE_DIR}/scripts'

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
        """Initialize a SlurmPool object."""
        self.ncpus_per_job = ncpus_per_job

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

    @classmethod
    def get_nodes(cls, sortByload=True) -> Dict:
        """Get nodes information from sinfo."""
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
            nodes = dict(
                OrderedDict(sorted(nodes.items(), key=lambda x: (x[1]['load'], x[1]['used_mem'], x[1]['used_cpus'])))
            )
        return nodes

    def _check_hypertreading(self, node_name) -> bool:
        """Check if hyperthreading is enabled."""
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
        if self.ncpus_per_job & 0x1:
            for node in self.nodes.keys():
                if self._check_hypertreading(node):
                    self.ncpus_per_job += 1
                    logger.warning(
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
        cmds: Union[str, List[str]],
        job_name: str = 'job',
        logging_level: int = logging.WARNING,
    ):
        """Submit a single job."""
        logger.setLevel(logging_level)
        Path(cls.SCRIPTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_DIR).mkdir(parents=True, exist_ok=True)
        templateLoader = FileSystemLoader(searchpath=f"{os.path.dirname(os.path.realpath(__file__))}/template")
        env = Environment(loader=templateLoader)
        template = env.get_template(cls.CPU_OpenMP_TEMPLATE)

        if isinstance(cmds, str):
            cmds = [cmds]
        output_from_parsed_template = template.render(
            job_name=job_name,
            partition=partition,
            node=node,
            cpus_per_task=cpus_per_task,
            cmds='\n'.join(cmds),
            log_dir=cls.LOG_DIR,
        )
        script_path = f'{cls.SCRIPTS_DIR}/{job_name}.sh'
        with open(script_path, 'w') as f:
            f.write(output_from_parsed_template)
        command = ['chmod', '755', script_path]
        _ = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        command = ['sbatch', script_path]
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        slurm_id = result.stdout.strip().split()[-1]
        logger.info(f'Sumbitted Task: {job_name} to {node}, containing {len(cmds)} jobs. Slurm ID: {slurm_id}')
        logger.debug(f'Commands: {cmds}')

    def multi_submit(
        self,
        cmds: List[str],
        job_name: str,
        logging_level: int = logging.WARNING,
        shuffle: bool = False,
        sleep_time: float = 0.5,
    ):
        """Submit jobs to multiple nodes."""
        if shuffle:
            import random

            random.shuffle(cmds)
        logger.setLevel(logging_level)
        logger.info(f'Found {len(self.nodes)} available nodes.')
        self.pool_size = min(self.pool_size, len(cmds))
        logger.info(f'{len(cmds):,} jobs to excute, allocated to {self.pool_size} tasks.')
        logger.info(f'Each task will use {self.ncpus_per_job} cpus.')

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
        logger.info(f'Used {len(used_nodes)} nodes.')
        logger.info(f'Each node will excute {max(used_nodes.values())} tasks in parallel.')
        logger.info(f'{used_nodes}')
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
                logger.info(f'{node}: {n_jobs} tasks')
                task = progress.add_task(f"Submitting to {node}...", total=n_jobs)
                for _ in range(n_jobs):
                    time.sleep(sleep_time)
                    start, end = ith * k + min(ith, m), (ith + 1) * k + min(ith + 1, m)
                    logger.info(f'Task {ith}: containing job {start}-{end-1}')
                    task_name = f'{job_name}_{ith:>03}'
                    self.single_submit(
                        self.nodes[node]['partition'],
                        node,
                        self.ncpus_per_job,
                        cmds[start:end],
                        task_name,
                        logging_level,
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
        with open(f'{self.FILE_DIR}/{self.time_now}.log', 'w') as f:
            logger.info(f'Writing task log to {self.FILE_DIR}/{self.time_now}.log')
            json.dump(task_log, f, indent=4)

    def starmap(self, func: Callable, params: Iterable[Iterable]):
        """Submit a list of commands to the cluster."""
        cmds = [func(*i) for i in params]
        self.multi_submit(cmds, func.__name__)

    def map(self, func: Callable, params: Iterable):
        """Submit a list of commands to the cluster."""
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
