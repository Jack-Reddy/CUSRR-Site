# pylint: disable=duplicate-code,unused-argument
"""
Tests for the /api/v1/abstractgrades routes.
"""
from website.models import AbstractGrade

def test_get_abstract_grades_empty(client):
    """GET /api/v1/abstractgrades/ returns empty list when no grades exist."""
    res = client.get("/api/v1/abstractgrades/")
    assert res.status_code == 200
    assert res.get_json() == []


def test_get_abstract_grades_nonempty(client, sample_abstract_grade_fixture):
    """GET /api/v1/abstractgrades/ returns existing grades."""
    res = client.get("/api/v1/abstractgrades/")
    data = res.get_json()
    assert res.status_code == 200
    assert len(data) == 1
    assert data[0]["criteria_1"] == sample_abstract_grade_fixture.criteria_1


def test_get_single_abstract_grade(client, sample_abstract_grade_fixture):
    """GET /api/v1/abstractgrades/<id> returns correct grade."""
    res = client.get(f"/api/v1/abstractgrades/{sample_abstract_grade_fixture.id}")
    assert res.status_code == 200
    assert res.get_json()["id"] == sample_abstract_grade_fixture.id


def test_get_single_abstractgrade_404(client):
    """GET /api/v1/abstractgrades/<id> returns 404 for nonexistent grade."""
    res = client.get("/api/v1/abstractgrades/9999")
    assert res.status_code == 404


def test_create_abstract_grade(client, sample_user_fixture, sample_presentation_fixture):
    """POST /api/v1/abstractgrades/ creates a new grade."""
    payload = {
        "user_id": sample_user_fixture.id,
        "presentation_id": sample_presentation_fixture.id,
        "criteria_1": 5,
        "criteria_2": 4,
        "criteria_3": 3
    }
    res = client.post("/api/v1/abstractgrades/", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["criteria_1"] == 5
    assert data["user_id"] == sample_user_fixture.id


def test_update_abstract_grade(client, sample_abstract_grade_fixture):
    """PUT /api/v1/abstractgrades/<id> updates an existing grade."""
    res = client.put(
        f"/api/v1/abstractgrades/{sample_abstract_grade_fixture.id}",
        json={"criteria_1": 2, "criteria_2": 3, "criteria_3": 4}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["criteria_1"] == 2


def test_delete_abstract_grade(client, sample_abstract_grade_fixture):
    """DELETE /api/v1/abstractgrades/<id> removes the grade."""
    res = client.delete(f"/api/v1/abstractgrades/{sample_abstract_grade_fixture.id}")
    assert res.status_code == 200
    assert res.get_json()["message"] == "Abstract grade deleted"
    assert AbstractGrade.query.get(sample_abstract_grade_fixture.id) is None


def test_delete_abstract_grade_404(client):
    """DELETE /api/v1/abstractgrades/<id> returns 404 for nonexistent grade."""
    res = client.delete("/api/v1/abstractgrades/9999")
    assert res.status_code == 404


def test_get_average_abstract_grades_by_presentation(client, multiple_abstract_grades_fixture):
    """GET /api/v1/abstractgrades/averages returns averages sorted high to low."""
    res = client.get("/api/v1/abstractgrades/averages")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert data[0]["num_grades"] == len(multiple_abstract_grades_fixture)
    avg_score = round(sum(
        g.criteria_1 + g.criteria_2 + g.criteria_3 for g in multiple_abstract_grades_fixture
    ) / len(multiple_abstract_grades_fixture), 2)
    assert data[0]["average_score"] == avg_score

def test_get_completed_presentations_for_user(client, 
                                              sample_user_fixture, 
                                              sample_presentation_fixture):
    """
    GET /api/v1/abstractgrades/completed/<user_id> returns presentations graded by a user.
    """
    # Create 2 grades by sample_user_fixture
    payload = {
        "user_id": sample_user_fixture.id,
        "presentation_id": sample_presentation_fixture.id,
        "criteria_1": 5,
        "criteria_2": 4,
        "criteria_3": 3
    }

    # grade the same presentation twice (should dedupe)
    client.post("/api/v1/abstractgrades/", json=payload)
    client.post("/api/v1/abstractgrades/", json=payload)

    # Hit the new route
    res = client.get(f"/api/v1/abstractgrades/completed/{sample_user_fixture.id}")

    assert res.status_code == 200
    data = res.get_json()

    # Expected shape: {"completed": [<presentation_id>]}
    assert isinstance(data, dict)
    assert "completed" in data
    assert data["completed"] == [sample_presentation_fixture.id]
