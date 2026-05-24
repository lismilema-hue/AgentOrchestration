"""Task Scheduler — Priority-based task queuing and dispatch."""

import asyncio
import heapq
import logging
import time
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class QueuePayloadDecoder:
    """Validates and decodes queue job payloads safely.

    Handles both modern and legacy queue record formats. Malformed or
    invalid payloads are rejected with a descriptive log entry instead
    of crashing the scheduler.
    """

    REQUIRED_FIELDS = ["type"]
    OPTIONAL_FIELDS = ["payload", "target_agent", "priority"]

    @staticmethod
    def validate(task: Dict) -> bool:
        """Return True if *task* is a well-formed job payload."""
        if not isinstance(task, dict):
            logger.warning("queue_payload_decoder: rejecting non-dict payload")
            return False

        for field in QueuePayloadDecoder.REQUIRED_FIELDS:
            value = task.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                logger.warning(
                    "queue_payload_decoder: missing or empty required field",
                    extra={"field": field},
                )
                return False

        payload = task.get("payload")
        if payload is not None and not isinstance(payload, dict):
            logger.warning(
                "queue_payload_decoder: payload must be a dict when present",
                extra={"actual_type": type(payload).__name__},
            )
            return False

        return True

    @staticmethod
    def decode(task: Any) -> Optional[Dict]:
        """Safely decode a raw input into a validated task dict.

        Returns the validated task dict, or *None* if the input is
        malformed and should be deferred / dropped.
        """
        if not isinstance(task, dict):
            logger.warning("queue_payload_decoder.decode: input is not a dict")
            return None

        if not QueuePayloadDecoder.validate(task):
            return None

        return task


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    def push(self, item: Any, priority: int = 0) -> None:
        heapq.heappush(self._queue, (-priority, self._counter, item))
        self._counter += 1

    def pop(self) -> Optional[Any]:
        if self._queue:
            return heapq.heappop(self._queue)[2]
        return None

    def peek(self) -> Optional[Any]:
        if self._queue:
            return self._queue[0][2]
        return None

    def __len__(self) -> int:
        return len(self._queue)


class TaskScheduler:
    def __init__(self):
        self._queues: Dict[str, PriorityQueue] = {}
        self._scheduled: Dict[str, float] = {}
        self._in_flight: Dict[str, Dict] = {}
        self._max_retries = 3
        self._decoder = QueuePayloadDecoder()
        # Idempotency set — tracks task IDs that have been fully
        # claimed (enqueued + dequeued) so retries don't re-process.
        self._claimed: set = set()

    def enqueue(self, task: Dict, queue: str = "default", priority: int = 0) -> Optional[str]:
        """Enqueue *task* after validating its payload.

        Returns the task id on success, or *None* when the payload is
        malformed and rejected.
        """
        decoded = self._decoder.decode(task)
        if decoded is None:
            logger.info(
                "scheduler.enqueue: rejecting malformed payload",
                extra={"queue": queue},
            )
            return None

        task_id = str(uuid4())
        decoded["id"] = task_id
        decoded["enqueued_at"] = time.time()
        if "retries" not in decoded:
            decoded["retries"] = 0

        if queue not in self._queues:
            self._queues[queue] = PriorityQueue()
        self._queues[queue].push(decoded, priority)
        return task_id

    def schedule(self, task: Dict, delay: float, queue: str = "default", priority: int = 0) -> Optional[str]:
        """Schedule a task for future execution after payload validation."""
        decoded = self._decoder.decode(task)
        if decoded is None:
            logger.info(
                "scheduler.schedule: rejecting malformed payload",
                extra={"queue": queue},
            )
            return None

        task_id = str(uuid4())
        decoded["id"] = task_id
        self._scheduled[task_id] = time.time() + delay
        return task_id

    async def dequeue(self, queue: str = "default", timeout: float = 1.0) -> Optional[Dict]:
        """Dequeue the highest-priority task from *queue*.

        Legacy / malformed records found at the head of the queue are
        safely skipped (logged and dropped) so they don't block valid
        work.
        """
        now = time.time()
        expired = [tid for tid, t in self._scheduled.items() if t <= now]
        for tid in expired:
            task = self._scheduled.pop(tid)
            if task:
                self.enqueue(task, queue)

        if queue in self._queues:
            while len(self._queues[queue]) > 0:
                task = self._queues[queue].pop()
                if task:
                    # Re-validate on dequeue to catch legacy records that
                    # may have been stored before validation was added.
                    decoded = self._decoder.decode(task)
                    if decoded is None:
                        logger.warning(
                            "scheduler.dequeue: skipping malformed legacy record",
                            extra={"queue": queue},
                        )
                        continue
                    # Idempotency: skip if this task was already claimed.
                    if decoded.get("id") in self._claimed:
                        logger.info(
                            "scheduler.dequeue: skipping already-claimed task",
                            extra={"task_id": decoded.get("id"), "queue": queue},
                        )
                        continue
                    self._in_flight[decoded["id"]] = decoded
                    return decoded
        return None

    def complete(self, task_id: str) -> bool:
        """Mark *task_id* as completed and record it for idempotency."""
        task = self._in_flight.pop(task_id, None)
        if task:
            self._claimed.add(task_id)
            return True
        return False

    def fail(self, task_id: str, queue: str = "default") -> bool:
        """Mark *task_id* as failed and retry if under max retries."""
        task = self._in_flight.pop(task_id, None)
        if task:
            task["retries"] += 1
            if task["retries"] < self._max_retries:
                self.enqueue(task, queue, priority=task.get("priority", 0))
                return True
        return False

# 2019-04-25T08:37:12 update
