#!/usr/bin/env python
"""Tests for `autosbatch` package."""

from autosbatch.logger import logger


def test_logger():
    """Test logger."""
    assert logger.name == "autosbatch.logger"
