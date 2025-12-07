# pylint: disable=unused-argument
"""
Tests for website route utilities.
"""

from website.routes.utils import format_average_grades


def test_format_average_grades_returns_json(client, sample_average_fixture):
    """Ensure the utility returns a JSON response with rounded scores and correct titles."""
    response = format_average_grades(sample_average_fixture)
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["presentation_id"] == sample_average_fixture[0].presentation_id
    assert item["presentation_title"] == "Test Presentation"
    assert item["average_score"] == round(sample_average_fixture[0].average_score, 2)
    assert item["num_grades"] == sample_average_fixture[0].num_grades


def test_format_average_grades_handles_missing_presentation(app):
    """Ensure it handles the case where a presentation is not found in the database."""
    class Avg:
        """average class for testing"""
        def __init__(self, presentation_id, average_score, num_grades):
            self.presentation_id = presentation_id
            self.average_score = average_score
            self.num_grades = num_grades

    missing_avg = [Avg(presentation_id=9999, average_score=3.5, num_grades=1)]
    response = format_average_grades(missing_avg)
    data = response.get_json()

    assert data[0]["presentation_title"] is None
    assert data[0]["average_score"] == 3.5
    assert data[0]["num_grades"] == 1
