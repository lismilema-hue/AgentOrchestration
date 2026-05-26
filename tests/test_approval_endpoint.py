"""Tests for the human-step approval endpoint.

Covers:
- Authorized approval on a workflow in an approvable state (pending/running).
- Unauthorized (conflict) approval on a workflow in a terminal state
  (completed, failed, skipped).
- Malformed / missing workflow ID (404).
"""

import pytest
from fastapi.testclient import TestClient
from src.api.server import create_app
from src.orchestrator.workflow import (
    WorkflowManager,
    Workflow,
    WorkflowStep,
    StepStatus,
    check_approval_state,
    WorkflowStateError,
)
from src.api.routes import workflow_manager


class TestCheckApprovalState:
    """Unit tests for the shared guard function."""

    def test_approvable_when_pending(self):
        w = Workflow("test")
        # Should not raise
        check_approval_state(w)

    def test_approvable_when_running(self):
        w = Workflow("test")
        w.status = StepStatus.RUNNING
        check_approval_state(w)

    def test_rejects_completed(self):
        w = Workflow("test")
        w.status = StepStatus.COMPLETED
        with pytest.raises(WorkflowStateError, match="completed"):
            check_approval_state(w)

    def test_rejects_failed(self):
        w = Workflow("test")
        w.status = StepStatus.FAILED
        with pytest.raises(WorkflowStateError, match="failed"):
            check_approval_state(w)

    def test_rejects_skipped(self):
        w = Workflow("test")
        w.status = StepStatus.SKIPPED
        with pytest.raises(WorkflowStateError, match="skipped"):
            check_approval_state(w)


class TestApproveHumanStep:
    """Unit tests for WorkflowManager.approve_human_step."""

    def setup_method(self):
        self.mgr = WorkflowManager()

    def test_approve_valid_pending_workflow(self):
        w = self.mgr.create_workflow("test-workflow")
        step = WorkflowStep("human-approval", lambda: None)
        w.add_step(step)
        assert self.mgr.approve_human_step(w.id)
        assert step.status == StepStatus.COMPLETED

    def test_approve_valid_running_workflow(self):
        w = self.mgr.create_workflow("test-workflow")
        w.status = StepStatus.RUNNING
        step = WorkflowStep("human-approval", lambda: None)
        w.add_step(step)
        assert self.mgr.approve_human_step(w.id)
        assert step.status == StepStatus.COMPLETED

    def test_approve_nonexistent_workflow_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.approve_human_step("nonexistent-id")

    def test_approve_completed_workflow_raises(self):
        w = self.mgr.create_workflow("test-workflow")
        w.status = StepStatus.COMPLETED
        with pytest.raises(WorkflowStateError, match="completed"):
            self.mgr.approve_human_step(w.id)

    def test_approve_failed_workflow_raises(self):
        w = self.mgr.create_workflow("test-workflow")
        w.status = StepStatus.FAILED
        with pytest.raises(WorkflowStateError, match="failed"):
            self.mgr.approve_human_step(w.id)

    def test_approve_skipped_workflow_raises(self):
        w = self.mgr.create_workflow("test-workflow")
        w.status = StepStatus.SKIPPED
        with pytest.raises(WorkflowStateError, match="skipped"):
            self.mgr.approve_human_step(w.id)


class TestApprovalEndpoint:
    """Integration tests for the POST /api/v2/workflows/{id}/approve-step route."""

    def setup_method(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        # Clear the shared workflow manager state before each test.
        workflow_manager._workflows.clear()

    def _create_workflow(self, status: str = "pending"):
        w = workflow_manager.create_workflow("test-workflow")
        step = WorkflowStep("human-approval", lambda: None)
        w.add_step(step)
        if status != "pending":
            w.status = StepStatus(status)
        return w

    def _post(self, url: str):
        return self.client.post(url, headers={"Authorization": "Bearer test-token"})

    def test_approve_pending_workflow_returns_200(self):
        w = self._create_workflow("pending")
        resp = self._post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["workflow_id"] == w.id

    def test_approve_running_workflow_returns_200(self):
        w = self._create_workflow("running")
        resp = self._post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    def test_approve_completed_workflow_returns_409(self):
        w = self._create_workflow("completed")
        resp = self._post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 409
        assert "completed" in resp.json()["detail"]

    def test_approve_failed_workflow_returns_409(self):
        w = self._create_workflow("failed")
        resp = self._post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 409
        assert "failed" in resp.json()["detail"]

    def test_approve_skipped_workflow_returns_409(self):
        w = self._create_workflow("skipped")
        resp = self._post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 409
        assert "skipped" in resp.json()["detail"]

    def test_approve_nonexistent_workflow_returns_404(self):
        resp = self._post("/api/v2/workflows/nonexistent-id/approve-step")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_approve_malformed_id_empty_string(self):
        resp = self._post("/api/v2/workflows/%20/approve-step")
        # A whitespace-only ID is still passed as a string — expect 404
        assert resp.status_code == 404

    def test_approve_malformed_id_special_chars(self):
        resp = self._post("/api/v2/workflows/%00/approve-step")
        # Null byte or special chars should still result in 404
        assert resp.status_code == 404

    def test_approve_unauthorized_no_token(self):
        w = self._create_workflow("pending")
        resp = self.client.post(f"/api/v2/workflows/{w.id}/approve-step")
        assert resp.status_code == 401
