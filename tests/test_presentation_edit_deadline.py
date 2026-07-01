"""Tests for presenter abstract editing deadline helpers."""
from datetime import datetime, timedelta

from website.routes import presentations


def test_abstract_edit_window_open_before_deadline(app):
    """Abstract edits are allowed before the configured deadline."""
    with app.app_context():
        app.config['ABSTRACT_SUBMISSION_DEADLINE'] = (
            datetime.now() + timedelta(days=1)
        ).isoformat()
        assert presentations._abstract_edit_window_open() is True
        app.config.pop('ABSTRACT_SUBMISSION_DEADLINE', None)


def test_abstract_edit_window_closed_after_deadline(app):
    """Abstract edits are blocked after the configured deadline."""
    with app.app_context():
        app.config['ABSTRACT_SUBMISSION_DEADLINE'] = (
            datetime.now() - timedelta(days=1)
        ).isoformat()
        assert presentations._abstract_edit_window_open() is False
        app.config.pop('ABSTRACT_SUBMISSION_DEADLINE', None)


def test_abstract_edit_window_open_without_deadline(app):
    """If no deadline is configured, abstract edits stay open."""
    with app.app_context():
        app.config.pop('ABSTRACT_SUBMISSION_DEADLINE', None)
        assert presentations._abstract_edit_window_open() is True
