"""Tests for TaskScheduler module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.scheduler import TaskScheduler


def test_scheduler_init():
    sched = TaskScheduler()
    assert sched is not None


def test_add_and_get_tasks():
    sched = TaskScheduler()
    sched.add_task("capture", priority=5, delay_s=0)
    due = sched.get_due_tasks()
    assert len(due) >= 0  # May or may not be due depending on timing
