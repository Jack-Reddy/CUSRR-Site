# pylint: disable=unused-argument
"""Tests for init.py create_app function."""

from website import create_app, db


def test_create_app_applies_config():
	"""create_app should apply provided test configuration values."""
	custom_config = {
		"TESTING": True,
		"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
		"SECRET_KEY": "unit-test-key",
	}

	app = create_app(custom_config)

	assert app.config["TESTING"] is True
	assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
	assert app.config["SECRET_KEY"] == "unit-test-key"


def test_create_app_registers_blueprints():
	"""Blueprint routes should be reachable after app creation."""
	app = create_app(
		{
			"TESTING": True,
			"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
		}
	)

	with app.app_context():
		db.create_all()

	client = app.test_client()

	users_res = client.get("/api/v1/users/")
	schedule_res = client.get("/api/v1/block-schedule/")

	assert users_res.status_code == 200
	assert users_res.get_json() == []
	assert schedule_res.status_code == 200
	assert schedule_res.get_json() == []


def test_create_app_renders_root_route():
	"""Root route should render successfully for a fresh app instance."""
	app = create_app(
		{
			"TESTING": True,
			"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
		}
	)

	with app.app_context():
		db.create_all()

	client = app.test_client()
	res = client.get("/")

	assert res.status_code == 200