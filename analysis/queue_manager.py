"""
queue_manager.py

Analysis queue for sequential VOD processing.

Milestone 1:
    - Queue jobs
    - Process one at a time
    - Track completed jobs

Future:
    - Pause queue
    - Resume queue
    - Persistent queue
    - Queue priorities
"""

from collections import deque
from threading import Lock


class QueueManager:

    def __init__(self):

        self._pending = deque()

        self._completed = []

        self._current = None

        self._running = False

        self._lock = Lock()

    # -----------------------------------------------------
    # Queue Operations
    # -----------------------------------------------------

    def enqueue(self, job):

        with self._lock:

            self._pending.append(job)

    def enqueue_many(self, jobs):

        with self._lock:

            self._pending.extend(jobs)

    def next_job(self):

        with self._lock:

            if not self._pending:

                return None

            self._current = self._pending.popleft()

            self._running = True

            return self._current

    def complete_current(self):

        with self._lock:

            if self._current is not None:

                self._completed.append(
                    self._current
                )

            self._current = None

            self._running = False

    def clear(self):

        with self._lock:

            self._pending.clear()

            self._completed.clear()

            self._current = None

            self._running = False

    # -----------------------------------------------------
    # Properties
    # -----------------------------------------------------

    @property
    def running(self):

        return self._running

    @property
    def current(self):

        return self._current

    @property
    def pending_count(self):

        return len(self._pending)

    @property
    def completed_count(self):

        return len(self._completed)

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

    def status(self):

        return {

            "running":

                self._running,

            "current":

                self._current,

            "pending":

                list(self._pending),

            "completed":

                list(self._completed)

        }