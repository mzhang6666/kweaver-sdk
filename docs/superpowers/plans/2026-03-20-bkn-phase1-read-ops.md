# BKN Phase 1: Entity Read Ops + Deep Get + Inspect

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ConceptGroups and Jobs resources, extend OT/RT/AT types with deep fields, add BKN inspect() composite method, register new resources on KWeaverClient, add CLI commands.

**Architecture:** Follow existing resource patterns (HttpClient DI, _parse_* functions, Pydantic models). New resources follow the same CRUD+list pattern as KnowledgeNetworksResource. inspect() is a composite method calling multiple endpoints and aggregating results.

**Tech Stack:** Python 3.10+, httpx, pydantic, click.

**Spec:** `docs/superpowers/specs/2026-03-20-bkn-read-observability-design.md` §3.1, §3.2, §4.1, §10

**Depends on:** Infra Phase 1 (complete)

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/kweaver/resources/concept_groups.py` | ConceptGroupsResource — CRUD + add/remove members |
| `src/kweaver/resources/jobs.py` | JobsResource — list, get_tasks, delete, wait |
| `tests/unit/test_concept_groups.py` | ConceptGroup resource tests |
| `tests/unit/test_jobs.py` | Job resource tests |
| `tests/unit/test_inspect.py` | inspect() composite method test |

### Modified Files

| File | Changes |
|------|---------|
| `src/kweaver/types.py` | Add ConceptGroup, Job, Task, DataPropertyDetail, MappingRule, ActionSource, ActionParam, BKNInspectReport, ServiceHealth |
| `src/kweaver/_client.py` | Add concept_groups, jobs resource accessors |
| `src/kweaver/resources/object_types.py` | Extend _parse to populate data_properties |
| `src/kweaver/resources/knowledge_networks.py` | Add inspect() method |

---

## Task 1: Add New Type Definitions

**Files:**
- Modify: `packages/python/src/kweaver/types.py`
- Test: `packages/python/tests/unit/test_types_bkn.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_types_bkn.py
"""Tests for BKN Phase 1 type definitions."""
from kweaver.types import (
    ConceptGroup, Job, Task as BKNTask,
    DataPropertyDetail, MappingRule, ActionSource, ActionParam,
    BKNInspectReport, ServiceHealth,
)


def test_concept_group_defaults():
    cg = ConceptGroup(id="cg-1", name="test", kn_id="kn-1")
    assert cg.branch == "main"
    assert cg.object_type_ids == []


def test_job_defaults():
    job = Job(id="j-1", kn_id="kn-1", type="build", status="pending")
    assert job.progress is None


def test_bkn_task():
    t = BKNTask(id="t-1", job_id="j-1", name="index", status="running")
    assert t.error is None


def test_data_property_detail():
    dp = DataPropertyDetail(name="age", type="integer")
    assert dp.indexed is False
    assert dp.mapped_field is None


def test_mapping_rule():
    mr = MappingRule(source_field="src", target_field="tgt")
    assert mr.operator is None


def test_action_source():
    src = ActionSource(type="internal")
    assert src.url is None


def test_action_param():
    p = ActionParam(name="limit", type="integer")
    assert p.required is False


def test_service_health():
    h = ServiceHealth(service="bkn-backend", status="healthy")
    assert h.version is None


def test_inspect_report():
    from kweaver.types import KnowledgeNetwork, KNStatistics
    report = BKNInspectReport(
        kn=KnowledgeNetwork(id="kn-1", name="test"),
        health=[ServiceHealth(service="bkn-backend", status="healthy")],
        stats=KNStatistics(),
    )
    assert len(report.health) == 1
    assert report.active_jobs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/python && python -m pytest tests/unit/test_types_bkn.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Add types to types.py**

Append to `packages/python/src/kweaver/types.py` (after existing model definitions, before BuildJob/BuildStatus/ActionExecution classes):

```python
# ── BKN Phase 1 entity types ───────────────────────────────────────────

class ConceptGroup(BaseModel):
    id: str
    name: str
    kn_id: str
    branch: str = "main"
    object_type_ids: list[str] = []
    creator: str | None = None
    updater: str | None = None
    create_time: str | None = None
    update_time: str | None = None


class Job(BaseModel):
    id: str
    kn_id: str
    type: str
    status: str  # pending | running | completed | failed
    progress: float | None = None
    creator: str | None = None
    create_time: str | None = None
    update_time: str | None = None


class Task(BaseModel):
    id: str
    job_id: str
    name: str
    status: str
    error: str | None = None
    create_time: str | None = None
    update_time: str | None = None


class DataPropertyDetail(BaseModel):
    name: str
    display_name: str | None = None
    type: str
    indexed: bool = False
    full_text: bool = False
    vector: bool = False
    required: bool = False
    default_value: Any = None
    enum_values: list[str] | None = None
    mapped_field: str | None = None


class MappingRule(BaseModel):
    source_field: str
    target_field: str
    operator: str | None = None


class ActionSource(BaseModel):
    type: str
    url: str | None = None
    method: str | None = None


class ActionParam(BaseModel):
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str | None = None


class ServiceHealth(BaseModel):
    service: str
    status: str
    version: str | None = None
    go_version: str | None = None
    arch: str | None = None


class BKNInspectReport(BaseModel):
    kn: KnowledgeNetwork
    health: list[ServiceHealth] = []
    stats: KNStatistics = Field(default_factory=KNStatistics)
    object_type_summary: list[dict[str, Any]] = []
    active_jobs: list[Job] = []
```

- [ ] **Step 4: Run tests**

Run: `cd packages/python && python -m pytest tests/unit/test_types_bkn.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add packages/python/src/kweaver/types.py packages/python/tests/unit/test_types_bkn.py
git commit -m "feat: add BKN Phase 1 type definitions (ConceptGroup, Job, inspect report)"
```

---

## Task 2: ConceptGroupsResource

**Files:**
- Create: `packages/python/src/kweaver/resources/concept_groups.py`
- Test: `packages/python/tests/unit/test_concept_groups.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_concept_groups.py
"""Tests for ConceptGroupsResource."""
import httpx
import pytest
from tests.conftest import RequestCapture, make_client


def test_list_concept_groups(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={"entries": [
            {"id": "cg-1", "name": "compute", "kn_id": "kn-1", "object_type_ids": ["ot-1"]},
        ]})
    client = make_client(handler, capture)
    cgs = client.concept_groups.list("kn-1")
    assert len(cgs) == 1
    assert cgs[0].name == "compute"
    assert "/knowledge-networks/kn-1/concept-groups" in capture.last_url()


def test_get_concept_group(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={
            "id": "cg-1", "name": "compute", "kn_id": "kn-1",
            "object_type_ids": ["ot-1", "ot-2"],
        })
    client = make_client(handler, capture)
    cg = client.concept_groups.get("kn-1", "cg-1")
    assert cg.id == "cg-1"
    assert len(cg.object_type_ids) == 2


def test_create_concept_group(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={
            "id": "cg-new", "name": "network", "kn_id": "kn-1",
        })
    client = make_client(handler, capture)
    cg = client.concept_groups.create("kn-1", name="network")
    assert cg.id == "cg-new"
    body = capture.last_body()
    assert body["name"] == "network"


def test_delete_concept_group(capture: RequestCapture):
    def handler(req):
        return httpx.Response(204)
    client = make_client(handler, capture)
    client.concept_groups.delete("kn-1", ["cg-1", "cg-2"])
    assert "cg-1,cg-2" in capture.last_url() or "cg-1" in capture.last_url()


def test_add_members(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={})
    client = make_client(handler, capture)
    client.concept_groups.add_members("kn-1", "cg-1", object_type_ids=["ot-1", "ot-2"])
    body = capture.last_body()
    assert "ot-1" in str(body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/python && python -m pytest tests/unit/test_concept_groups.py -v`
Expected: FAIL — `client.concept_groups` doesn't exist

- [ ] **Step 3: Create resource file**

Create `packages/python/src/kweaver/resources/concept_groups.py`:

```python
"""SDK resource: concept groups (ontology-manager)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kweaver.types import ConceptGroup

if TYPE_CHECKING:
    from kweaver._http import HttpClient

_BASE = "/api/ontology-manager/v1/knowledge-networks"


def _parse_cg(data: dict[str, Any]) -> ConceptGroup:
    return ConceptGroup(
        id=data.get("id", ""),
        name=data.get("name", ""),
        kn_id=data.get("kn_id", ""),
        branch=data.get("branch", "main"),
        object_type_ids=data.get("object_type_ids") or [],
        creator=data.get("creator"),
        updater=data.get("updater"),
        create_time=data.get("create_time"),
        update_time=data.get("update_time"),
    )


class ConceptGroupsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, kn_id: str, *, name: str) -> ConceptGroup:
        data = self._http.post(f"{_BASE}/{kn_id}/concept-groups", json={"name": name, "branch": "main"})
        return _parse_cg(data)

    def list(self, kn_id: str, *, offset: int = 0, limit: int = 20) -> list[ConceptGroup]:
        data = self._http.get(
            f"{_BASE}/{kn_id}/concept-groups",
            params={"offset": offset, "limit": limit},
        )
        entries = data.get("entries", data.get("data", [])) if isinstance(data, dict) else data
        return [_parse_cg(e) for e in entries]

    def get(self, kn_id: str, cg_id: str) -> ConceptGroup:
        data = self._http.get(f"{_BASE}/{kn_id}/concept-groups/{cg_id}")
        return _parse_cg(data)

    def update(self, kn_id: str, cg_id: str, *, name: str | None = None) -> ConceptGroup:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        data = self._http.put(f"{_BASE}/{kn_id}/concept-groups/{cg_id}", json=body)
        return _parse_cg(data)

    def delete(self, kn_id: str, cg_ids: list[str]) -> None:
        ids_str = ",".join(cg_ids)
        self._http.delete(f"{_BASE}/{kn_id}/concept-groups/{ids_str}")

    def add_members(self, kn_id: str, cg_id: str, *, object_type_ids: list[str]) -> None:
        self._http.post(
            f"{_BASE}/{kn_id}/concept-groups/{cg_id}/object-types",
            json={"object_type_ids": object_type_ids},
        )

    def remove_members(self, kn_id: str, cg_id: str, *, object_type_ids: list[str]) -> None:
        ids_str = ",".join(object_type_ids)
        self._http.delete(f"{_BASE}/{kn_id}/concept-groups/{cg_id}/object-types/{ids_str}")
```

- [ ] **Step 4: Register on KWeaverClient**

In `packages/python/src/kweaver/_client.py`, add import and resource:
```python
from kweaver.resources.concept_groups import ConceptGroupsResource
```
And in `__init__`:
```python
self.concept_groups = ConceptGroupsResource(self._http)
```

- [ ] **Step 5: Run tests**

Run: `cd packages/python && python -m pytest tests/unit/test_concept_groups.py -v`
Expected: 5 passed

- [ ] **Step 6: Run ALL tests**

Run: `cd packages/python && python -m pytest tests/unit/ -v --tb=short`

- [ ] **Step 7: Commit**

```bash
git add packages/python/src/kweaver/resources/concept_groups.py packages/python/src/kweaver/_client.py packages/python/tests/unit/test_concept_groups.py
git commit -m "feat: add ConceptGroupsResource — CRUD + member management"
```

---

## Task 3: JobsResource

**Files:**
- Create: `packages/python/src/kweaver/resources/jobs.py`
- Test: `packages/python/tests/unit/test_jobs.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_jobs.py
"""Tests for JobsResource."""
import httpx
import pytest
from unittest.mock import patch
from tests.conftest import RequestCapture, make_client


def test_list_jobs(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={"entries": [
            {"id": "j-1", "kn_id": "kn-1", "type": "build", "status": "completed"},
        ]})
    client = make_client(handler, capture)
    jobs = client.jobs.list("kn-1")
    assert len(jobs) == 1
    assert jobs[0].status == "completed"


def test_list_jobs_with_status_filter(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={"entries": []})
    client = make_client(handler, capture)
    client.jobs.list("kn-1", status="running")
    assert "status=running" in capture.last_url()


def test_get_tasks(capture: RequestCapture):
    def handler(req):
        return httpx.Response(200, json={"entries": [
            {"id": "t-1", "job_id": "j-1", "name": "index_pod", "status": "completed"},
        ]})
    client = make_client(handler, capture)
    tasks = client.jobs.get_tasks("kn-1", "j-1")
    assert len(tasks) == 1
    assert tasks[0].name == "index_pod"


def test_delete_jobs(capture: RequestCapture):
    def handler(req):
        return httpx.Response(204)
    client = make_client(handler, capture)
    client.jobs.delete("kn-1", ["j-1", "j-2"])
    assert "j-1,j-2" in capture.last_url() or "j-1" in capture.last_url()


def test_wait_returns_completed_job():
    """wait() should poll until job reaches terminal state."""
    call_count = {"n": 0}
    def handler(req):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            return httpx.Response(200, json={
                "id": "j-1", "kn_id": "kn-1", "type": "build", "status": "running",
            })
        return httpx.Response(200, json={
            "id": "j-1", "kn_id": "kn-1", "type": "build", "status": "completed",
        })
    client = make_client(handler)
    with patch("kweaver.resources.jobs.time.sleep"):
        job = client.jobs.wait("kn-1", "j-1")
    assert job.status == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/python && python -m pytest tests/unit/test_jobs.py -v`

- [ ] **Step 3: Create resource file**

Create `packages/python/src/kweaver/resources/jobs.py`:

```python
"""SDK resource: jobs & tasks (ontology-manager)."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from kweaver.types import Job, Task

if TYPE_CHECKING:
    from kweaver._http import HttpClient

_BASE = "/api/ontology-manager/v1/knowledge-networks"
_TERMINAL_STATES = frozenset({"completed", "failed"})
_MAX_BACKOFF = 30.0


def _parse_job(data: dict[str, Any]) -> Job:
    return Job(
        id=data.get("id", ""),
        kn_id=data.get("kn_id", ""),
        type=data.get("type", ""),
        status=data.get("status", ""),
        progress=data.get("progress"),
        creator=data.get("creator"),
        create_time=data.get("create_time"),
        update_time=data.get("update_time"),
    )


def _parse_task(data: dict[str, Any]) -> Task:
    return Task(
        id=data.get("id", ""),
        job_id=data.get("job_id", ""),
        name=data.get("name", ""),
        status=data.get("status", ""),
        error=data.get("error"),
        create_time=data.get("create_time"),
        update_time=data.get("update_time"),
    )


class JobsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, kn_id: str, *, status: str | None = None, offset: int = 0, limit: int = 20) -> list[Job]:
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if status:
            params["status"] = status
        data = self._http.get(f"{_BASE}/{kn_id}/jobs", params=params)
        entries = data.get("entries", data.get("data", [])) if isinstance(data, dict) else data
        return [_parse_job(e) for e in entries]

    def get_tasks(self, kn_id: str, job_id: str) -> list[Task]:
        data = self._http.get(f"{_BASE}/{kn_id}/jobs/{job_id}/tasks")
        entries = data.get("entries", data.get("data", [])) if isinstance(data, dict) else data
        return [_parse_task(e) for e in entries]

    def delete(self, kn_id: str, job_ids: list[str]) -> None:
        ids_str = ",".join(job_ids)
        self._http.delete(f"{_BASE}/{kn_id}/jobs/{ids_str}")

    def wait(self, kn_id: str, job_id: str, *, timeout: float = 300, interval: float = 2.0) -> Job:
        """Poll job until terminal state. Uses exponential backoff (max 30s)."""
        deadline = time.monotonic() + timeout
        current_interval = interval
        while True:
            data = self._http.get(f"{_BASE}/{kn_id}/jobs/{job_id}")
            job = _parse_job(data)
            if job.status in _TERMINAL_STATES:
                return job
            if time.monotonic() + current_interval > deadline:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s (status: {job.status})")
            time.sleep(current_interval)
            current_interval = min(current_interval * 2, _MAX_BACKOFF)
```

- [ ] **Step 4: Register on KWeaverClient**

In `packages/python/src/kweaver/_client.py`, add:
```python
from kweaver.resources.jobs import JobsResource
```
And in `__init__`:
```python
self.jobs = JobsResource(self._http)
```

- [ ] **Step 5: Run tests**

Run: `cd packages/python && python -m pytest tests/unit/test_jobs.py -v`
Expected: 5 passed

- [ ] **Step 6: Run ALL tests**

Run: `cd packages/python && python -m pytest tests/unit/ -v --tb=short`

- [ ] **Step 7: Commit**

```bash
git add packages/python/src/kweaver/resources/jobs.py packages/python/src/kweaver/_client.py packages/python/tests/unit/test_jobs.py
git commit -m "feat: add JobsResource — list, tasks, delete, wait with exponential backoff"
```

---

## Task 4: Extend OT/RT/AT Types with Deep Fields

**Files:**
- Modify: `packages/python/src/kweaver/types.py` (already done in Task 1 — DataPropertyDetail etc.)
- Modify: `packages/python/src/kweaver/resources/object_types.py` (_parse to include data_properties)
- Test: `packages/python/tests/unit/test_full_get.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_full_get.py
"""Tests for deep get() — full property parsing."""
import httpx
from tests.conftest import RequestCapture, make_client


def test_object_type_get_parses_data_properties(capture: RequestCapture):
    """get() should parse data_properties from API response."""
    def handler(req):
        return httpx.Response(200, json={
            "id": "ot-1", "name": "Pod", "kn_id": "kn-1",
            "data_properties": [
                {"name": "cpu", "type": "float", "indexed": True, "mapped_field": "cpu_cores"},
                {"name": "name", "type": "string"},
            ],
        })
    client = make_client(handler, capture)
    ot = client.object_types.get("kn-1", "ot-1")
    assert len(ot.data_properties) == 2
    assert ot.data_properties[0].name == "cpu"
    assert ot.data_properties[0].indexed is True
    assert ot.data_properties[0].mapped_field == "cpu_cores"
    assert ot.data_properties[1].type == "string"


def test_object_type_get_empty_data_properties(capture: RequestCapture):
    """get() with no data_properties should return empty list."""
    def handler(req):
        return httpx.Response(200, json={
            "id": "ot-1", "name": "Pod", "kn_id": "kn-1",
        })
    client = make_client(handler, capture)
    ot = client.object_types.get("kn-1", "ot-1")
    assert ot.data_properties == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/python && python -m pytest tests/unit/test_full_get.py -v`
Expected: FAIL — ObjectType has no `data_properties` attribute

- [ ] **Step 3: Extend ObjectType model and _parse**

Read `packages/python/src/kweaver/types.py` to find the ObjectType class definition. Add `data_properties: list[DataPropertyDetail] = []` field.

Read `packages/python/src/kweaver/resources/object_types.py` to find `_parse_object_type()`. Add parsing of data_properties:

```python
from kweaver.types import DataPropertyDetail
# ... in _parse_object_type:
data_properties = [
    DataPropertyDetail(**dp) for dp in d.get("data_properties", [])
    if isinstance(dp, dict)
]
# ... include in ObjectType construction:
# data_properties=data_properties,
```

- [ ] **Step 4: Run tests**

Run: `cd packages/python && python -m pytest tests/unit/test_full_get.py tests/unit/test_object_types.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add packages/python/src/kweaver/types.py packages/python/src/kweaver/resources/object_types.py packages/python/tests/unit/test_full_get.py
git commit -m "feat: extend ObjectType with data_properties deep parsing"
```

---

## Task 5: BKN inspect() Composite Method

**Files:**
- Modify: `packages/python/src/kweaver/resources/knowledge_networks.py`
- Test: `packages/python/tests/unit/test_inspect.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_inspect.py
"""Tests for KN inspect() composite method."""
import httpx
from tests.conftest import make_client
from kweaver.types import BKNInspectReport


def test_inspect_returns_report():
    """inspect() should aggregate KN info + stats + jobs."""
    def handler(req):
        url = str(req.url)
        if req.method == "GET" and url.endswith("/kn-1"):
            return httpx.Response(200, json={
                "id": "kn-1", "name": "k8s", "tags": [],
                "statistics": {
                    "object_types_total": 3,
                    "relation_types_total": 1,
                    "action_types_total": 0,
                    "concept_groups_total": 1,
                },
            })
        if "jobs" in url:
            return httpx.Response(200, json={"entries": []})
        return httpx.Response(200, json={})

    client = make_client(handler)
    report = client.knowledge_networks.inspect("kn-1")
    assert isinstance(report, BKNInspectReport)
    assert report.kn.id == "kn-1"
    assert report.stats.object_types_total == 3
    assert report.active_jobs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/python && python -m pytest tests/unit/test_inspect.py -v`

- [ ] **Step 3: Add inspect() to KnowledgeNetworksResource**

Read `packages/python/src/kweaver/resources/knowledge_networks.py`. Add this method:

```python
from kweaver.types import BKNInspectReport, Job

def inspect(self, kn_id: str, *, full: bool = False) -> BKNInspectReport:
    """One-shot diagnosis: KN info + stats + active jobs."""
    kn = self.get(kn_id, include_statistics=True)

    # Get active jobs (best effort)
    active_jobs: list[Job] = []
    try:
        from kweaver.resources.jobs import _parse_job
        data = self._http.get(
            f"/api/ontology-manager/v1/knowledge-networks/{kn_id}/jobs",
            params={"status": "running", "limit": 20},
        )
        entries = data.get("entries", data.get("data", [])) if isinstance(data, dict) else []
        active_jobs = [_parse_job(e) for e in entries]
    except Exception:
        pass  # partial failure tolerance

    return BKNInspectReport(
        kn=kn,
        stats=kn.statistics or KNStatistics(),
        active_jobs=active_jobs,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd packages/python && python -m pytest tests/unit/test_inspect.py tests/unit/test_knowledge_networks.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add packages/python/src/kweaver/resources/knowledge_networks.py packages/python/tests/unit/test_inspect.py
git commit -m "feat: add inspect() composite method to KnowledgeNetworksResource"
```

---

## Task 6: Final Regression

- [ ] **Step 1: Run full test suite**

Run: `cd packages/python && python -m pytest tests/unit/ -v --tb=short`
Expected: All pass

- [ ] **Step 2: Verify coverage**

Run: `cd packages/python && python -m pytest tests/unit/ --cov=kweaver --cov-report=term-missing 2>&1 | tail -5`
Expected: ≥ 65%

- [ ] **Step 3: Commit any remaining files**

```bash
git status
# If any unstaged changes:
git add -A && git commit -m "chore: BKN Phase 1 cleanup"
```

- [ ] **Step 4: Push**

```bash
git push
```
