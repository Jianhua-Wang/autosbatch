"""Console script for autosbatch."""

from autosbatch import SlurmPool
import click
import logging


@click.command()
@click.option('-p', '--pool-size', 'pool_size', type=int,
              help="How many jobs do you want to run in parallel. Use all resources if None.")
@click.option('-n', '--ncpus-per-job', 'ncpus_per_job', type=int, help="How many cpus per job uses, default=2",
              default=2)
@click.option('-M', '--max-jobs-per-node', 'max_jobs_per_node', type=int,
              help="how many jobs can a node run in parallel at most")
@click.option('-N', '--node-list', 'node_list', type=str,
              help="specify the nodes you want to use, separated by commas, e.g. 'cpu01,cpu02,cpu03', use as many as "
                   "you can if None")
@click.option('-j', '--job-name', 'job_name', type=str, help="job name prefix, default=test", default='test')
@click.argument('cmdfile', type=click.Path(exists=True), )
def cli(pool_size, ncpus_per_job, max_jobs_per_node, node_list, cmdfile, job_name):
    """
        autosbatch --ncpus-per-job 10 cmd.sh
    """
    with open(cmdfile, 'r') as f:
        cmds = f.readlines()
    cmds = [cmd.strip() for cmd in cmds]
    if node_list:
        node_list = node_list.split(',')
    max_pool_size = SlurmPool(ncpus_per_job=ncpus_per_job)
    max_pool_size = max_pool_size.pool_size
    p = SlurmPool(min(max_pool_size, len(cmds)), ncpus_per_job, max_jobs_per_node, node_list)
    click.echo(f'N jobs: {len(cmds)}')
    click.echo(f'Pool size: {p.pool_size}')
    click.echo(f'N cpus per job: {p.ncpus_per_job}')
    click.echo(f'Max jobs per node: {p.max_jobs_per_node}')
    p.multi_submit(cmds, len(cmds), job_name, logging_level=logging.INFO)


if __name__ == '__main__':
    cli()
