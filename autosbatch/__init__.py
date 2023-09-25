"""Top-level package for autosbatch."""
import logging

from rich.logging import RichHandler

from autosbatch.autosbatch import SlurmPool

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
__author__ = """Jianhua Wang"""
__email__ = 'jianhua.mert@gmail.com'
__version__ = '0.2.7'
