"""Tests for TaskScheduler module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.scheduler import TaskScheduler


def test_scheduler_init():
    sched = TaskScheduler()
    assert sched is not None


def test_scheduler_has_methods():
    sched = TaskScheduler()
    assert hasattr(sched, 'add_periodic_task')
    assert hasattr(sched, 'tick')
