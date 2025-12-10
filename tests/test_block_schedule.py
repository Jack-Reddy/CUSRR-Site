# pylint: disable=unused-argument
"""
Tests for the /api/v1/block-schedule routes.
"""

from datetime import datetime
from website.models import BlockSchedule
from website import db 

def test_get_schedules_empty(client):
    """GET /api/v1/block-schedule/ returns an empty list when no schedules exist."""
    res = client.get("/api/v1/block-schedule/")
    assert res.status_code == 200
    assert res.get_json() == []


def test_get_schedules_nonempty(client, sample_block_fixture):
    """GET /api/v1/block-schedule/ returns existing schedules."""
    res = client.get("/api/v1/block-schedule/")
    data = res.get_json()
    assert res.status_code == 200
    assert len(data) == 1
    assert data[0]["title"] == sample_block_fixture.title


def test_get_single_schedule(client, sample_block_fixture):
    """GET /api/v1/block-schedule/<id> returns correct schedule."""
    res = client.get(f"/api/v1/block-schedule/{sample_block_fixture.id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == sample_block_fixture.id
    assert data["title"] == sample_block_fixture.title


def test_get_single_schedule_404(client):
    """GET /api/v1/block-schedule/<id> returns 404 for nonexistent schedule."""
    res = client.get("/api/v1/block-schedule/9999")
    assert res.status_code == 404


def test_create_schedule(client):
    """POST /api/v1/block-schedule/ creates a new block schedule."""
    payload = {
        "day": "Day 2",
        "start_time": "2025-12-07T09:00",
        "end_time": "2025-12-07T10:00",
        "title": "Test Block",
        "description": "Block description",
        "location": "Room 101",
        "block_type": "poster",
        "sub_length": 10
    }
    res = client.post("/api/v1/block-schedule/", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "Test Block"
    assert data["day"] == "Day 2"
    # Check that start_time and end_time were parsed correctly
    start_dt = datetime.strptime(payload["start_time"], "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(payload["end_time"], "%Y-%m-%dT%H:%M")
    assert datetime.fromisoformat(data["start_time"]) == start_dt
    assert datetime.fromisoformat(data["end_time"]) == end_dt


def test_update_schedule(client, sample_block_fixture):
    """PUT /api/v1/block-schedule/<id> updates an existing block."""
    payload = {"title": "Updated Block"}
    res = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Updated Block"


def test_delete_schedule(client, sample_block_fixture):
    """DELETE /api/v1/block-schedule/<id> removes the block."""
    res = client.delete(f"/api/v1/block-schedule/{sample_block_fixture.id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["message"] == "Schedule deleted"
    assert db.session.get(BlockSchedule, sample_block_fixture.id) is None 
    

def test_get_schedules_by_day(client, sample_block_fixture):
    """GET /api/v1/block-schedule/day/<day> returns schedules for that day."""
    res = client.get(f"/api/v1/block-schedule/day/{sample_block_fixture.day}")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) >= 1
    assert data[0]["day"] == sample_block_fixture.day


def test_get_unique_days(client, sample_block_fixture):
    """GET /api/v1/block-schedule/days returns a list of unique days."""
    res = client.get("/api/v1/block-schedule/days")
    assert res.status_code == 200
    days = res.get_json()
    assert sample_block_fixture.day in days
