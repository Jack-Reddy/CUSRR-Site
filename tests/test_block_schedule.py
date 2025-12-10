# pylint: disable=unused-argument
"""
Tests for the /api/v1/block-schedule routes.
"""

from datetime import datetime, timedelta
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


def test_update_schedule_end_time(client, sample_block_fixture):
    """PUT /api/v1/block-schedule/<id> updates end_time correctly and handles parsing failure."""

    # --- Valid snake_case end_time ---
    new_end_time = (datetime.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
    payload_snake = {"end_time": new_end_time.isoformat(timespec='minutes')}
    
    res_snake = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=payload_snake)
    assert res_snake.status_code == 200
    data_snake = res_snake.get_json()
    updated_time_snake = datetime.fromisoformat(data_snake["end_time"]).replace(second=0, microsecond=0)
    assert updated_time_snake == new_end_time

    # --- Invalid snake_case end_time (parsing fails) ---
    invalid_payload = {"end_time": "invalid-datetime-format"}
    res_invalid = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=invalid_payload)
    assert res_invalid.status_code == 200
    # Ensure DB value did not change
    updated_schedule = db.session.get(BlockSchedule, sample_block_fixture.id)
    assert updated_schedule.end_time.replace(second=0, microsecond=0) == new_end_time

    # --- Valid camelCase endTime ---
    new_end_time2 = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    payload_camel = {"endTime": new_end_time2.isoformat(timespec='minutes')}
    
    res_camel = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=payload_camel)
    assert res_camel.status_code == 200
    data_camel = res_camel.get_json()
    updated_time_camel = datetime.fromisoformat(data_camel["end_time"]).replace(second=0, microsecond=0)
    assert updated_time_camel == new_end_time2

    # --- Invalid camelCase endTime ---
    invalid_payload2 = {"endTime": "not-a-date"}
    res_invalid2 = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=invalid_payload2)
    assert res_invalid2.status_code == 200
    updated_schedule = db.session.get(BlockSchedule, sample_block_fixture.id)
    assert updated_schedule.end_time.replace(second=0, microsecond=0) == new_end_time2


def test_update_schedule_start_time(client, sample_block_fixture):
    """PUT /api/v1/block-schedule/<id> updates start_time correctly and handles parsing failure."""

    # --- Valid snake_case start_time ---
    new_start_time = (datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0)
    payload_snake = {"start_time": new_start_time.isoformat(timespec='minutes')}

    res_snake = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=payload_snake)
    assert res_snake.status_code == 200
    data_snake = res_snake.get_json()
    updated_time_snake = datetime.fromisoformat(data_snake["start_time"]).replace(second=0, microsecond=0)
    assert updated_time_snake == new_start_time

    # --- Invalid snake_case start_time ---
    invalid_payload = {"start_time": "invalid-format"}
    res_invalid = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=invalid_payload)
    assert res_invalid.status_code == 200
    updated_schedule = db.session.get(BlockSchedule, sample_block_fixture.id)
    assert updated_schedule.start_time.replace(second=0, microsecond=0) == new_start_time

    # --- Valid camelCase startTime ---
    new_start_time2 = (datetime.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
    payload_camel = {"startTime": new_start_time2.isoformat(timespec='minutes')}

    res_camel = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=payload_camel)
    assert res_camel.status_code == 200
    data_camel = res_camel.get_json()
    updated_time_camel = datetime.fromisoformat(data_camel["start_time"]).replace(second=0, microsecond=0)
    assert updated_time_camel == new_start_time2

    # --- Invalid camelCase startTime ---
    invalid_payload2 = {"startTime": "not-a-date"}
    res_invalid2 = client.put(f"/api/v1/block-schedule/{sample_block_fixture.id}", json=invalid_payload2)
    assert res_invalid2.status_code == 200
    updated_schedule = db.session.get(BlockSchedule, sample_block_fixture.id)
    assert updated_schedule.start_time.replace(second=0, microsecond=0) == new_start_time2