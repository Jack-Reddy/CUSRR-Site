"""Tests for presenter abstract editing permissions."""
from datetime import datetime, timedelta

from website import db
from website.models import Presentation, User


def _make_presenter_with_presentation():
    presentation = Presentation(
        title="Original Title",
        abstract="Original abstract",
        department="Biology",
    )
    db.session.add(presentation)
    db.session.flush()

    user = User(
        firstname="Presenter",
        lastname="Student",
        email="presenter@example.com",
        auth="presenter",
        presentation_id=presentation.id,
    )
    db.session.add(user)
    db.session.commit()
    return presentation, user


def test_presenter_can_edit_own_abstract_before_deadline(client, app):
    """A presenter can edit their own submitted abstract before the deadline."""
    with app.app_context():
        presentation, user = _make_presenter_with_presentation()
        presentation_id = presentation.id
        app.config['TESTING'] = False
        app.config['ABSTRACT_SUBMISSION_DEADLINE'] = (datetime.now() + timedelta(days=1)).isoformat()

    with client.session_transaction() as sess:
        sess['user'] = {'email': user.email}

    response = client.put(
        f"/api/v1/presentations/{presentation_id}",
        json={"title": "Updated Title", "abstract": "Updated abstract", "department": "Chemistry"},
    )

    app.config['TESTING'] = True
    app.config.pop('ABSTRACT_SUBMISSION_DEADLINE', None)

    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Updated Title"
    assert data["abstract"] == "Updated abstract"
    assert data["department"] == "Chemistry"


def test_presenter_cannot_edit_after_deadline(client, app):
    """A presenter cannot edit their submitted abstract after the deadline."""
    with app.app_context():
        presentation, user = _make_presenter_with_presentation()
        presentation_id = presentation.id
        app.config['TESTING'] = False
        app.config['ABSTRACT_SUBMISSION_DEADLINE'] = (datetime.now() - timedelta(days=1)).isoformat()

    with client.session_transaction() as sess:
        sess['user'] = {'email': user.email}

    response = client.put(
        f"/api/v1/presentations/{presentation_id}",
        json={"abstract": "Too late"},
    )

    app.config['TESTING'] = True
    app.config.pop('ABSTRACT_SUBMISSION_DEADLINE', None)

    assert response.status_code == 403
    assert "deadline" in response.get_json()["error"].lower()
