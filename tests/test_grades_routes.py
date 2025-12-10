# pylint: disable=duplicate-code,unused-argument
"""
Tests for the /api/v1/grades routes.
"""

from website.models import Grade
from website import db

def test_get_grades_empty(client):
    """GET /api/v1/grades/ returns an empty list when no grades exist."""
    res = client.get("/api/v1/grades/")
    assert res.status_code == 200
    assert res.get_json() == []


def test_get_grades_nonempty(client, sample_grade_fixture):
    """GET /api/v1/grades/ returns existing grades."""
    res = client.get("/api/v1/grades/")
    data = res.get_json()
    assert res.status_code == 200
    assert len(data) == 1
    assert data[0]["criteria_1"] == sample_grade_fixture.criteria_1


def test_get_single_grade(client, sample_grade_fixture):
    """GET /api/v1/grades/<id> returns the correct grade."""
    res = client.get(f"/api/v1/grades/{sample_grade_fixture.id}")
    assert res.status_code == 200
    assert res.get_json()["id"] == sample_grade_fixture.id


def test_get_single_grade_404(client):
    """GET /api/v1/grades/<id> returns 404 for nonexistent grade."""
    res = client.get("/api/v1/grades/9999")
    assert res.status_code == 404


def test_create_grade(client, sample_user_fixture, sample_presentation_fixture):
    """POST /api/v1/grades/ creates a new grade and prevents duplicates."""
    payload = {
        "user_id": sample_user_fixture.id,
        "presentation_id": sample_presentation_fixture.id,
        "criteria_1": 5,
        "criteria_2": 4,
        "criteria_3": 3
    }

    # First creation should succeed
    res = client.post("/api/v1/grades/", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["criteria_1"] == 5
    assert data["user_id"] == sample_user_fixture.id

    # Attempt to create a second grade for the same user and presentation
    res2 = client.post("/api/v1/grades/", json=payload)
    assert res2.status_code == 400
    assert "already" in res2.get_json()["error"].lower()



def test_update_grade(client, sample_grade_fixture):
    """PUT /api/v1/grades/<id> updates an existing grade."""
    res = client.put(
        f"/api/v1/grades/{sample_grade_fixture.id}",
        json={"criteria_1": 2, "criteria_2": 3, "criteria_3": 4}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["criteria_1"] == 2


def test_delete_grade(client, sample_grade_fixture):
    """DELETE /api/v1/grades/<id> removes the grade."""
    res = client.delete(f"/api/v1/grades/{sample_grade_fixture.id}")
    assert res.status_code == 200
    assert res.get_json()["message"] == "Grade deleted"
    assert db.session.get(Grade, sample_grade_fixture.id) is None


def test_delete_grade_404(client):
    """DELETE /api/v1/grades/<id> returns 404 for nonexistent grade."""
    res = client.delete("/api/v1/grades/9999")
    assert res.status_code == 404


def test_get_average_grades_by_presentation(client, multiple_grades_fixture):
    """GET /api/v1/grades/averages returns averages sorted high to low."""
    res = client.get("/api/v1/grades/averages")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert data[0]["num_grades"] == len(multiple_grades_fixture)
    avg_score = round(sum(
        g.criteria_1 + g.criteria_2 + g.criteria_3 for g in multiple_grades_fixture
    ) / len(multiple_grades_fixture), 2)
    assert data[0]["average_score"] == avg_score
