"""Console script for autosbatch."""

import logging

import click

from autosbatch import SlurmPool

# TODO: replace click with typer


@click.command()
@click.option(
    '-p',
    '--pool-size',
    'pool_size',
    type=int,
    help="How many jobs do you want to run in parallel. Use all resources if None.",
)
@click.option(
    '-n', '--ncpus-per-job', 'ncpus_per_job', type=int, help="How many cpus per job uses, default=2", default=1
)
@click.option(
    '-M', '--max-jobs-per-node', 'max_jobs_per_node', type=int, help="how many jobs can a node run in parallel at most"
)
@click.option(
    '-N',
    '--node-list',
    'node_list',
    type=str,
    help="specify the nodes you want to use, separated by commas, e.g. 'cpu01,cpu02,cpu03', use as many as "
    "you can if None",
)
@click.option('-j', '--job-name', 'job_name', type=str, help="job name prefix, default=test", default='test')
@click.argument(
    'cmdfile',
    type=click.Path(exists=True),
)
def main(pool_size, ncpus_per_job, max_jobs_per_node, node_list, cmdfile, job_name):
    """
    autosbatch --ncpus-per-job 10 cmd.sh
    """
    with open(cmdfile, 'r') as f:
        cmds = f.readlines()
    cmds = [cmd.strip() for cmd in cmds]
    if node_list:
        node_list = node_list.split(',')
    p = SlurmPool(ncpus_per_job=ncpus_per_job, max_jobs_per_node=max_jobs_per_node, node_list=node_list)
    p.multi_submit(cmds, job_name, logging_level=logging.INFO)


if __name__ == '__main__':
    main()
