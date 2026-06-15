"""Tests for program quick-view rows and continuous program IDs."""
from datetime import timedelta

from website import db
from website.models import BlockSchedule, Presentation, User


def test_program_identifier_continues_across_blocks(client, app, sample_block_fixture):
    """Poster IDs should continue across poster blocks instead of restarting."""
    with app.app_context():
        second_block = BlockSchedule(
            day=sample_block_fixture.day,
            start_time=sample_block_fixture.end_time + timedelta(minutes=30),
            end_time=sample_block_fixture.end_time + timedelta(hours=1),
            title="Second Poster Block",
            description="More posters",
            location="Room B",
            block_type="poster",
            sub_length=15,
            is_presentation=True,
        )
        db.session.add(second_block)
        db.session.flush()

        presentations = [
            Presentation(
                title="First Poster",
                schedule_id=sample_block_fixture.id,
                num_in_block=0,
            ),
            Presentation(
                title="Second Poster",
                schedule_id=sample_block_fixture.id,
                num_in_block=1,
            ),
            Presentation(
                title="Third Poster",
                schedule_id=second_block.id,
                num_in_block=0,
            ),
        ]
        db.session.add_all(presentations)
        db.session.commit()

    res = client.get("/api/v1/presentations/type/Poster")
    assert res.status_code == 200
    ids_by_title = {row["title"]: row["program_identifier"] for row in res.get_json()}

    assert ids_by_title["First Poster"] == "poster-1"
    assert ids_by_title["Second Poster"] == "poster-2"
    assert ids_by_title["Third Poster"] == "poster-3"


def test_program_table_includes_presentations_and_meals(client, app, sample_block_fixture):
    """The program quick-view table should include presentations plus lunch/dinner rows."""
    with app.app_context():
        presentation = Presentation(
            title="Quick View Talk",
            abstract="Abstract",
            subject="Testing",
            schedule_id=sample_block_fixture.id,
            num_in_block=0,
        )
        db.session.add(presentation)
        db.session.flush()

        presenter = User(
            firstname="Jane",
            lastname="Doe",
            email="jane.program@example.com",
            auth="presenter",
            presentation_id=presentation.id,
        )
        lunch = BlockSchedule(
            day=sample_block_fixture.day,
            start_time=sample_block_fixture.start_time + timedelta(hours=2),
            end_time=sample_block_fixture.start_time + timedelta(hours=3),
            title="Lunch",
            description="Lunch break",
            location="Dining Hall",
            block_type="lunch",
            is_presentation=False,
        )
        db.session.add_all([presenter, lunch])
        db.session.commit()

    res = client.get("/api/v1/presentations/program-table")
    assert res.status_code == 200
    rows = res.get_json()

    assert any(
        row["title"] == "Quick View Talk" and row["authors"] == "Jane Doe"
        for row in rows
    )
    meal_rows = [row for row in rows if row["kind"] == "event"]
    assert any(row["authors"] == "lunch" and row["event_type"] == "lunch" for row in meal_rows)
