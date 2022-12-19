"""Console script for autosbatch."""

import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from autosbatch import SlurmPool, __version__
from autosbatch.logger import logger

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
app = typer.Typer(context_settings=CONTEXT_SETTINGS, add_completion=False)

config = {
    'logging_level': logging.WARNING,
}


@app.command()
def single_job(
    ncpus: int = typer.Option(1, '--ncpus', '-n', help='Number of cpus.'),
    node: str = typer.Option(None, '--node', '-N', help='Node to submit job to.'),
    partition: str = typer.Option(None, '--partition', '-P', help='Partition to submit jobs to.'),
    job_name: str = typer.Option('job', '--job-name', '-j', help='Name of the job.'),
    cmd: List[str] = typer.Argument(..., help='Command to run.'),
):
    """Submit a single job to slurm cluster."""
    cmd = [' '.join(cmd)]
    if node:
        node_list: Optional[List] = [node]
    else:
        node_list = None
    p = SlurmPool(
        pool_size=1,
        ncpus_per_job=ncpus,
        node_list=node_list,
        partition=partition,
    )
    p.multi_submit(cmds=cmd, job_name=job_name, logging_level=config['logging_level'])


@app.command()
def multi_job(
    pool_size: int = typer.Option(
        None, '--pool-size', '-p', min=0, max=1000, help='Number of jobs to submit at the same time.'
    ),
    ncpus_per_job: int = typer.Option(1, '--ncpus-per-job', '-n', help='Number of cpus per job.'),
    max_jobs_per_node: int = typer.Option(
        None, '--max-jobs-per-node', '-m', help='Maximum number of jobs to submit to a single node.'
    ),
    node_list: List[str] = typer.Option(
        None, '--node-list', '-l', help='List of nodes to submit jobs to. e.g. "-l node1 -l node2 -l node3"'
    ),
    partition: str = typer.Option(None, '--partition', '-P', help='Partition to submit jobs to.'),
    job_name: str = typer.Option('job', '--job-name', '-j', help='Name of the job.'),
    cmdfile: Path = typer.Argument(..., help='Path to the command file.'),
):
    """Submit multiple jobs to slurm cluster."""
    with open(cmdfile, 'r') as f:
        cmds = f.readlines()
    cmds = [cmd.strip() for cmd in cmds]

    p = SlurmPool(
        pool_size=pool_size,
        ncpus_per_job=ncpus_per_job,
        max_jobs_per_node=max_jobs_per_node,
        node_list=node_list,
        partition=partition,
    )
    p.multi_submit(cmds=cmds, job_name=job_name, logging_level=config['logging_level'])


@app.command()
def clean():
    """Remove all scripts and logs."""
    SlurmPool.clean()
    logger.setLevel(config['logging_level'])
    logger.info('Cleaned all scripts and logs.')


@app.callback(invoke_without_command=True, no_args_is_help=True)
def main(
    version: bool = typer.Option(False, '--version', '-V', help='Show version.'),
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Show verbose info.'),
    dev: bool = typer.Option(False, '--dev', help='Show dev info.'),
):
    """Submit jobs to slurm cluster, without writing slurm script files."""
    console = Console()
    console.rule("[bold blue]AutoSbatch[/bold blue]")
    if version:
        typer.echo(f'AutoSbatch version: {__version__}')
        raise typer.Exit()
    if verbose:
        config['logging_level'] = logging.INFO
        logger.info('Verbose mode is on.')
    if dev:
        config['logging_level'] = logging.DEBUG
        logger.debug('Dev mode is on.')


if __name__ == '__main__':
    app()
