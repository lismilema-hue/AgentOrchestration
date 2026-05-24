import pytest
from src.orchestrator.scheduler import TaskScheduler, QueuePayloadDecoder


class TestQueuePayloadDecoder:
    def test_validate_valid_minimal(self):
        assert QueuePayloadDecoder.validate({"type": "test"})

    def test_validate_valid_with_payload(self):
        assert QueuePayloadDecoder.validate({"type": "test", "payload": {"data": 1}})

    def test_validate_rejects_non_dict(self):
        assert not QueuePayloadDecoder.validate("not a dict")
        assert not QueuePayloadDecoder.validate(42)
        assert not QueuePayloadDecoder.validate(None)
        assert not QueuePayloadDecoder.validate([])

    def test_validate_missing_type(self):
        assert not QueuePayloadDecoder.validate({"payload": {}})

    def test_validate_empty_type(self):
        assert not QueuePayloadDecoder.validate({"type": ""})
        assert not QueuePayloadDecoder.validate({"type": "   "})

    def test_validate_non_dict_payload(self):
        assert not QueuePayloadDecoder.validate({"type": "test", "payload": "string"})
        assert not QueuePayloadDecoder.validate({"type": "test", "payload": 42})
        assert not QueuePayloadDecoder.validate({"type": "test", "payload": [1, 2]})

    def test_decode_valid(self):
        result = QueuePayloadDecoder.decode({"type": "test", "payload": {}})
        assert result == {"type": "test", "payload": {}}

    def test_decode_invalid_returns_none(self):
        assert QueuePayloadDecoder.decode("bad") is None
        assert QueuePayloadDecoder.decode({"type": ""}) is None
        assert QueuePayloadDecoder.decode(42) is None


class TestTaskScheduler:
    def setup_method(self):
        self.scheduler = TaskScheduler()

    def test_enqueue_valid_task(self):
        task_id = self.scheduler.enqueue({"type": "test", "payload": {}})
        assert task_id is not None

    def test_enqueue_rejects_malformed(self):
        task_id = self.scheduler.enqueue({"payload": {}})
        assert task_id is None
        # also verify nothing was added to any queue
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert task is None

    def test_enqueue_rejects_non_dict(self):
        task_id = self.scheduler.enqueue("string_payload")
        assert task_id is None

    def test_dequeue_valid_task(self):
        self.scheduler.enqueue({"type": "test", "payload": {"data": 1}})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert task is not None
        assert task["type"] == "test"
        assert task["payload"] == {"data": 1}

    def test_dequeue_skips_malformed_record(self):
        """Legacy malformed records at head of queue are safely skipped."""
        # Manually push a malformed item directly into the queue
        # (bypass validation) to simulate a legacy record.
        pq = self.scheduler._queues.setdefault("default", __import__(
            "src.orchestrator.scheduler", fromlist=["PriorityQueue"]
        ).PriorityQueue())
        pq.push({"bad": "legacy record"})
        # Now push a valid one behind it
        self.scheduler.enqueue({"type": "valid", "payload": {}})

        import asyncio
        # The malformed record should be skipped, and the valid one returned.
        task = asyncio.run(self.scheduler.dequeue())
        assert task is not None
        assert task["type"] == "valid"

    def test_enqueue_multiple_priorities(self):
        self.scheduler.enqueue({"type": "low"}, priority=1)
        self.scheduler.enqueue({"type": "high"}, priority=10)
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert task["type"] == "high"

    def test_complete_task(self):
        self.scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert self.scheduler.complete(task["id"])

    def test_fail_task_with_retry(self):
        self.scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert self.scheduler.fail(task["id"])

    def test_complete_adds_to_claimed_idempotency(self):
        self.scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        self.scheduler.complete(task["id"])
        # completing should have added the id to the claimed set
        assert task["id"] in self.scheduler._claimed

    def test_dequeue_skips_already_claimed(self):
        """A task that was already claimed should not be dequeued again."""
        # Enqueue, dequeue, and complete a task
        task_id = self.scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert task is not None
        self.scheduler.complete(task["id"])

        # Manually push the same task back into the queue (simulating a
        # retry delivery of an already-processed message)
        pq = self.scheduler._queues.setdefault("default", __import__(
            "src.orchestrator.scheduler", fromlist=["PriorityQueue"]
        ).PriorityQueue())
        pq.push(task)

        # Dequeue again — should skip the already-claimed task
        result = asyncio.run(self.scheduler.dequeue())
        assert result is None

    def test_schedule_valid(self):
        task_id = self.scheduler.schedule({"type": "future"}, delay=10)
        assert task_id is not None

    def test_schedule_rejects_malformed(self):
        task_id = self.scheduler.schedule({"payload": {}}, delay=10)
        assert task_id is None

    def test_dequeue_empty_queue(self):
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        assert task is None

    def test_fail_max_retries(self):
        self.scheduler.enqueue({"type": "test"})
        import asyncio
        task = asyncio.run(self.scheduler.dequeue())
        task_id = task["id"]
        # fail once — task is re-enqueued with a new id
        assert self.scheduler.fail(task_id, "default")
        # dequeue the retried task
        task2 = asyncio.run(self.scheduler.dequeue())
        assert task2 is not None
        assert task2["retries"] == 1
        # fail again — second re-enqueue
        assert self.scheduler.fail(task2["id"], "default")
        task3 = asyncio.run(self.scheduler.dequeue())
        assert task3 is not None
        assert task3["retries"] == 2
        # third fail crosses max_retries (3), retry is NOT enqueued
        assert not self.scheduler.fail(task3["id"], "default")
