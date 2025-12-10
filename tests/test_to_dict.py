"""
Tests for the `to_dict` methods of User, Presentation, Grade, AbstractGrade, BlockSchedule
with full branch coverage.
"""

from datetime import datetime, timedelta

from website.models import User, Presentation, Grade, AbstractGrade, BlockSchedule
from website import db

def test_presentation_to_dict_branches(app, sample_block_fixture):
    """Test Presentation.to_dict() with various time and schedule combinations."""
    with app.app_context():
        # Case 1: time is set → used directly
        pres1 = Presentation(title="Time Set", time=datetime.now(), schedule_id=sample_block_fixture.id)
        db.session.add(pres1)
        db.session.commit()
        d1 = pres1.to_dict()
        assert d1["time"] is not None

        # Case 2: time is None, schedule exists, num_in_block and sub_length defined
        pres2 = Presentation(
            title="Computed Time",
            time=None,
            schedule_id=sample_block_fixture.id,
            num_in_block=2
        )
        db.session.add(pres2)
        db.session.commit()
        d2 = pres2.to_dict()
        expected_time = (sample_block_fixture.start_time +
                         timedelta(minutes=2 * sample_block_fixture.sub_length)).replace(microsecond=0)
        actual_time = datetime.strptime(d2["time"], "%Y-%m-%dT%H:%M:%S")
        assert actual_time == expected_time

        # Case 3: time is None, schedule exists, num_in_block is None → fallback to start_time
        pres3 = Presentation(time=None, schedule_id=sample_block_fixture.id, num_in_block=None, title="Fallback")
        db.session.add(pres3)
        db.session.commit()
        d3 = pres3.to_dict()
        expected_time3 = sample_block_fixture.start_time.replace(microsecond=0)
        actual_time3 = datetime.strptime(d3["time"], "%Y-%m-%dT%H:%M:%S")
        assert actual_time3 == expected_time3

        # Case 4: no time, no schedule → time None
        pres4 = Presentation(time=None, schedule_id=None, title="No Schedule")
        db.session.add(pres4)
        db.session.commit()
        d4 = pres4.to_dict()
        assert d4["time"] is None
        assert d4["room"] is None
        assert d4["type"] is None


def test_grade_to_dict_branches(app, sample_grade_fixture):
    """Test Grade.to_dict() with and without grader/presentation relationships."""
    with app.app_context():
        grade = sample_grade_fixture

        # Normal case
        d = grade.to_dict()
        assert d["grader_name"] == f"{grade.grader.firstname} {grade.grader.lastname}"
        assert d["presentation_title"] == grade.presentation.title

        # Case: grader is None
        grade.grader = None
        db.session.commit()
        d2 = grade.to_dict()
        assert d2["grader_name"] is None

        # Case: presentation is None
        grade.presentation = None
        db.session.commit()
        d3 = grade.to_dict()
        assert d3["presentation_title"] is None


def test_abstract_grade_to_dict_branches(app, sample_abstract_grade_fixture):
    """Test AbstractGrade.to_dict() with and without grader/presentation."""
    with app.app_context():
        ag = sample_abstract_grade_fixture

        d = ag.to_dict()
        assert d["grader_name"] == f"{ag.grader.firstname} {ag.grader.lastname}"
        assert d["presentation_title"] == ag.presentation.title

        ag.grader = None
        ag.presentation = None
        db.session.commit()
        d2 = ag.to_dict()
        assert d2["grader_name"] is None
        assert d2["presentation_title"] is None


def test_block_schedule_to_dict_branches(app, sample_block_fixture):
    """Test BlockSchedule.to_dict() and length computation."""
    with app.app_context():
        block = sample_block_fixture
        d = block.to_dict()
        assert d["id"] == block.id
        assert d["length"] == (block.end_time - block.start_time).total_seconds() / 60

        # Case: start_time or end_time is None
        block.start_time = None
        block.end_time = None
        db.session.commit()
        d2 = block.to_dict()
        assert d2["start_time"] is None
        assert d2["end_time"] is None
        assert d2["length"] is None
