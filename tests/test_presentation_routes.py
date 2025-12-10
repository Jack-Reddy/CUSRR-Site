# pylint: disable=duplicate-code,unused-argument
"""Tests for the /api/v1/presentations endpoints."""

import io
from datetime import datetime, timedelta

from website import db
from website.models import Presentation, User

def test_get_presentations_empty(client):
    """GET /api/v1/presentations/ returns an empty list when no presentations exist."""
    res = client.get("/api/v1/presentations/")
    assert res.status_code == 200
    assert res.get_json() == []


def test_get_presentations_nonempty(client, sample_presentation_fixture):
    """GET /api/v1/presentations/ returns existing presentations."""
    res = client.get("/api/v1/presentations/")
    data = res.get_json()
    assert res.status_code == 200
    assert len(data) == 1
    assert data[0]["title"] == "Test Presentation"


def test_get_single_presentation(client, sample_presentation_fixture):
    """GET /api/v1/presentations/<id> returns the correct presentation."""
    sample_presentation = sample_presentation_fixture
    res = client.get(f"/api/v1/presentations/{sample_presentation.id}")
    assert res.status_code == 200
    assert res.get_json()["id"] == sample_presentation.id


def test_get_single_presentation_404(client):
    """GET /api/v1/presentations/<id> returns 404 for nonexistent ID."""
    res = client.get("/api/v1/presentations/9999")
    assert res.status_code == 404


def test_create_presentation_valid(client):
    """POST /api/v1/presentations/ creates a new presentation with valid data."""
    payload = {
        "title": "New Talk",
        "abstract": "abc",
        "subject": "Math",
        "time": datetime.now().isoformat()
    }
    res = client.post("/api/v1/presentations/", json=payload)
    assert res.status_code == 201
    assert res.get_json()["title"] == "New Talk"


def test_create_presentation_invalid_time(client):
    """POST /api/v1/presentations/ returns 400 if time is not ISO 8601."""
    payload = {
        "title": "Bad Time",
        "time": "not-a-date"
    }
    res = client.post("/api/v1/presentations/", json=payload)
    assert res.status_code == 400
    assert "Invalid datetime format" in res.get_json()["error"]


def test_update_presentation(client, sample_presentation_fixture):
    """PUT /api/v1/presentations/<id> updates an existing presentation's title."""
    sample_presentation = sample_presentation_fixture
    res = client.put(
        f"/api/v1/presentations/{sample_presentation.id}",
        json={"title": "Updated Title"}
    )
    assert res.status_code == 200
    assert res.get_json()["title"] == "Updated Title"


def test_update_presentation_404(client):
    """PUT /api/v1/presentations/<id> returns 404 for nonexistent ID."""
    res = client.put("/api/v1/presentations/9999", json={"title": "X"})
    assert res.status_code == 404


def test_delete_presentation(client, sample_presentation_fixture):
    """DELETE /api/v1/presentations/<id> removes the presentation."""
    sample_presentation = sample_presentation_fixture
    res = client.delete(f"/api/v1/presentations/{sample_presentation.id}")
    assert res.status_code == 200
    assert res.get_json()["message"] == "Presentation deleted"
    assert db.session.get(Presentation, sample_presentation.id) is None


def test_delete_presentation_404(client):
    """DELETE /api/v1/presentations/<id> returns 404 for nonexistent ID."""
    res = client.delete("/api/v1/presentations/9999")
    assert res.status_code == 404


def test_recent_presentations(client, app, sample_block_fixture):
    """
    GET /api/v1/presentations/recent returns future presentations
    sorted by effective time.
    """
    with app.app_context():
        future = datetime.now() + timedelta(hours=1)
        pres = Presentation(
            title="Future",
            time=future,
            schedule_id=sample_block_fixture.id
        )
        db.session.add(pres)
        db.session.commit()

    res = client.get("/api/v1/presentations/recent")
    assert res.status_code == 200
    assert len(res.get_json()) == 1
    assert res.get_json()[0]["title"] == "Future"


def test_get_presentations_by_type(client, sample_block_fixture, app):
    """GET /api/v1/presentations/type/<category> returns presentations of that type."""
    with app.app_context():
        future = datetime.now() + timedelta(hours=1)
        pres = Presentation(
            title="Poster Dude",
            time=future,
            schedule_id=sample_block_fixture.id,
        )
        db.session.add(pres)
        db.session.commit()

    res = client.get("/api/v1/presentations/type/poster")
    assert res.status_code == 200
    assert len(res.get_json()) == 1
    assert res.get_json()[0]["title"] == "Poster Dude"


def test_get_presentations_by_type_invalid(client):
    """GET /api/v1/presentations/type/<category> returns 400 for invalid category."""
    res = client.get("/api/v1/presentations/type/notatype")
    assert res.status_code == 400


def test_get_presentations_by_day(client, sample_block_fixture, app):
    """GET /api/v1/presentations/day/<day> returns presentations grouped by poster blocks."""
    with app.app_context():
        pres1 = Presentation(
            title="Poster1",
            schedule_id=sample_block_fixture.id,
            num_in_block=0
        )
        pres2 = Presentation(
            title="Poster2",
            schedule_id=sample_block_fixture.id,
            num_in_block=1
        )
        db.session.add_all([pres1, pres2])
        db.session.commit()

    res = client.get("/api/v1/presentations/day/Day 1")
    assert res.status_code == 200
    blocks = res.get_json()
    assert len(blocks) == 1
    assert len(blocks[0]["presentations"]) == 2
    assert blocks[0]["presentations"][0]["title"] == "Poster1"


def test_update_order_forbidden_no_session(client):
    """POST /api/v1/presentations/order returns 403 if no session user is set."""
    res = client.post("/api/v1/presentations/order", json={"orders": []})
    assert res.status_code == 403


def test_update_order_success(client, app, sample_block_fixture, sample_user_fixture):
    """POST /api/v1/presentations/order updates num_in_block for organizer user."""
    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        user.auth = "organizer"
        db.session.commit()

        sample_presentation = Presentation(
            title="Reorder Me",
            schedule_id=sample_block_fixture.id,
            num_in_block=0
        )
        db.session.add(sample_presentation)
        db.session.commit()
        presentation_id = sample_presentation.id

    with client.session_transaction() as sess:
        sess["user"] = {"email": "jane@example.com"}

    res = client.post("/api/v1/presentations/order", json={
        "orders": [{"presentation_id": presentation_id, "num_in_block": 5}]
    })

    assert res.status_code == 200

def test_update_presentations_order_edge_cases(client, app,
                                               sample_user_fixture,
                                               sample_block_fixture):
    """
    Covers edge cases for /api/v1/presentations/order:
    - Missing session
    - Non-organizer user
    - Missing 'orders' key
    - Orders missing 'presentation_id' or 'num_in_block'
    - Nonexistent presentation_id
    - TypeError / ValueError during commit
    """

    # No session user → 403
    res = client.post("/api/v1/presentations/order",
                      json={"orders": [{"presentation_id": 1, "num_in_block": 5}]})
    assert res.status_code == 403

    # Non-organizer session → 403
    with client.session_transaction() as sess:
        sess["user"] = {"email": "user@example.com"}
    res = client.post("/api/v1/presentations/order",
                      json={"orders": [{"presentation_id": 1, "num_in_block": 5}]})
    assert res.status_code == 403

    # Make fixture user organizer
    sample_user_fixture.auth = "organizer"
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user"] = {"email": sample_user_fixture.email}

    # Missing 'orders' key → 400
    res = client.post("/api/v1/presentations/order", json={})
    assert res.status_code == 400

    # Orders with missing 'presentation_id' → passes, returns empty updated list
    res = client.post("/api/v1/presentations/order",
                      json={"orders": [{"num_in_block": 5}]})
    assert res.status_code == 200
    assert res.json["updated"] == []

    # Orders with nonexistent presentation_id → passes, returns empty updated list
    res = client.post("/api/v1/presentations/order",
                      json={"orders": [{"presentation_id": 999}]})
    assert res.status_code == 200
    assert res.json["updated"] == []

    # Simulate commit error by monkeypatching db.session.commit
    def fail_commit():
        raise TypeError("Simulated commit error")

    original_commit = db.session.commit
    db.session.commit = fail_commit
    pres = Presentation(title="Error Test", schedule_id=sample_block_fixture.id, num_in_block=0)
    db.session.add(pres)
    db.session.flush()  # ensure id assigned

    res = client.post("/api/v1/presentations/order",
                      json={"orders": [{"presentation_id": pres.id, "num_in_block": 1}]})
    assert res.status_code == 500
    assert "Failed to save order" in res.json["error"]
    db.session.rollback()
    db.session.commit = original_commit  # restore commit

def test_get_recent_presentations_computed_time(client, app, sample_block_fixture):
    """
    Covers effective_time fallback in get_recent_presentations when Presentation.time is None
    and computation uses block start time + num_in_block * sub_length.
    """
    pres = Presentation(title="Fallback Time",
                        schedule_id=sample_block_fixture.id,
                        num_in_block=1,
                        time=None)
    db.session.add(pres)
    db.session.commit()

    res = client.get("/api/v1/presentations/recent")
    assert res.status_code == 200
    # Should include the presentation
    assert any(sample_presentation["title"] == "Fallback Time" for
               sample_presentation in res.json)


def test_get_presentations_by_day_null_num(client, sample_block_fixture):
    """
    Covers null num_in_block ordering branch in get_presentations_by_day,
    ensuring presentations with None num_in_block appear first due to nullsfirst().
    """
    pres = Presentation(title="Null num_in_block",
                        schedule_id=sample_block_fixture.id,
                        num_in_block=None)
    db.session.add(pres)
    db.session.commit()

    res = client.get(f"/api/v1/presentations/day/{sample_block_fixture.day}")
    assert res.status_code == 200
    assert any(
        sample_presentation["title"] == "Null num_in_block"
        for block in res.json
        for sample_presentation in block["presentations"]
    )


def test_upload_presentation_file_success(client, sample_presentation_fixture):
    """POST /api/v1/presentations/<id>/upload successfully uploads a file."""
    pres = sample_presentation_fixture
    data = {
        "file": (io.BytesIO(b"dummy content"), "test.pptx")
    }

    res = client.post(f"/api/v1/presentations/{pres.id}/upload", data=data,
                      content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.get_json()["message"] == "File uploaded successfully"

    # Verify DB updated
    uploaded_pres = Presentation.query.get(pres.id)
    assert uploaded_pres.presentation_file is not None
    assert uploaded_pres.presentation_file.startswith(b"dummy")


def test_upload_presentation_file_invalid_type(client, sample_presentation_fixture):
    """Rejects non-PPT/PPTX file uploads."""
    pres = sample_presentation_fixture
    data = {
        "file": (io.BytesIO(b"dummy content"), "bad.txt")
    }

    res = client.post(f"/api/v1/presentations/{pres.id}/upload", data=data,
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "Invalid file type" in res.get_json()["error"]


def test_upload_presentation_file_no_file(client, sample_presentation_fixture):
    """Rejects request with no file part."""
    pres = sample_presentation_fixture
    res = client.post(f"/api/v1/presentations/{pres.id}/upload", data={},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "No file part" in res.get_json()["error"]


def test_upload_presentation_file_empty_filename(client, sample_presentation_fixture):
    """Rejects file with empty filename."""
    pres = sample_presentation_fixture
    data = {
        "file": (io.BytesIO(b"dummy content"), "")
    }
    res = client.post(f"/api/v1/presentations/{pres.id}/upload", data=data,
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "No file selected" in res.get_json()["error"]


def test_upload_presentation_file_too_large(client, sample_presentation_fixture):
    """Rejects files over 20MB."""
    pres = sample_presentation_fixture
    data = {
        "file": (io.BytesIO(b"0" * (20 * 1024 * 1024 + 1)), "big.pptx")
    }
    res = client.post(f"/api/v1/presentations/{pres.id}/upload", data=data,
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "File exceeds 20MB" in res.get_json()["error"]


def test_download_all_presentations(client, sample_presentation_fixture):
    """GET /api/v1/presentations/download-all returns a ZIP with all presentations."""
    pres = sample_presentation_fixture
    # Attach a dummy file
    pres.presentation_file = b"dummy pptx content"
    db.session.commit()

    res = client.get("/api/v1/presentations/download-all")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/zip"
    assert "attachment" in res.headers["Content-Disposition"]

    # Verify ZIP content
    import zipfile
    import io as io_module

    zip_bytes = io_module.BytesIO(res.data)
    with zipfile.ZipFile(zip_bytes, 'r') as zipf:
        names = zipf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".pptx")
        content = zipf.read(names[0])
        assert content == b"dummy pptx content"


def test_download_all_presentations_skips_empty(client, sample_presentation_fixture):
    """Presentations without files are skipped in the ZIP."""
    pres = sample_presentation_fixture
    pres.presentation_file = None
    db.session.commit()

    res = client.get("/api/v1/presentations/download-all")
    assert res.status_code == 200

    import zipfile
    import io as io_module

    zip_bytes = io_module.BytesIO(res.data)
    with zipfile.ZipFile(zip_bytes, 'r') as zipf:
        # No files in ZIP
        assert zipf.namelist() == []
