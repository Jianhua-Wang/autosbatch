"""test autosbatch.py."""

from autosbatch.autosbatch import SlurmPool
import logging
from pathlib import Path


def test_slurm_pool():
    """Test SlurmPool."""
    p = SlurmPool()
    assert p.pool_size == 1000
    assert p.ncpus_per_job == 2
    assert p.max_jobs_per_node == 76
    assert len(p.node_list) == 54


def test_slurm_pool_init():
    """Test SlurmPool init."""
    p = SlurmPool(
        pool_size=1,
        ncpus_per_job=2,
        max_jobs_per_node=3,
        node_list=['cpu01', 'cpu02'],
        partition='cpuPartition',
    )
    assert p.pool_size == 1
    assert p.ncpus_per_job == 2
    assert p.max_jobs_per_node == 3
    assert p.node_list == ['cpu01', 'cpu02']


def test_slurm_pool_multi_submit():
    """Test SlurmPool multi_submit."""
    p = SlurmPool()
    p.multi_submit(cmds=['echo hello'], job_name='test_job', logging_level=logging.DEBUG)
    assert p.pool_size == 1
    assert p.ncpus_per_job == 2
    assert p.max_jobs_per_node == 76


def test_slurm_pool_clean():
    """Test SlurmPool clean."""
    p = SlurmPool()
    p.clean()
    assert not Path(p.dir_path).exists()


def test_slurm_pool_get_node_list():
    """Test SlurmPool get_node_list."""
    p = SlurmPool()
    node_list = p.get_nodes()
    assert len(node_list) == 54


def test_slurm_pool_single_submit():
    """Test SlurmPool single_submit."""
    p = SlurmPool()
    p.single_submit(
        partition='cpuPartition',
        node='cpu01',
        cpus_per_task=1,
        cmds=['echo hello'],
        job_name='test_job',
        logging_level=logging.DEBUG,
    )
    assert p.pool_size == 1000
    assert p.ncpus_per_job == 2
    assert p.max_jobs_per_node == 76
