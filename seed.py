from models import db, User, Presentation

def seed_data():
    """Populate the database with initial test data."""

    # --- Presentations ---
    p1 = Presentation(
        title="AI in Education",
        abstract="Exploring how AI is transforming learning.",
        subject="Artificial Intelligence",
        time="2025-11-05 10:00",
        room="Room A",
        type="Lecture"
    )

    p2 = Presentation(
        title="Climate Change and Policy",
        abstract="A discussion on environmental policy.",
        subject="Environmental Studies",
        time="2025-11-05 13:00",
        room="Room B",
        type="Panel"
    )

    p3 = Presentation(
        title="Modern Web Security",
        abstract="Best practices for securing web applications.",
        subject="Cybersecurity",
        time="2025-11-06 09:30",
        room="Room C",
        type="Workshop"
    )

    db.session.add_all([p1, p2, p3])
    db.session.commit()

    # --- Users ---
    u1 = User(firstname="Alice", lastname="Johnson", email="alice@example.com", presentation_id=p1.id, activity="Speaker")
    u2 = User(firstname="Bob", lastname="Smith", email="bob@example.com", presentation_id=p1.id, activity="Co-presenter")
    u3 = User(firstname="Catherine", lastname="Lee", email="catherine@example.com", presentation_id=p2.id, activity="Moderator")
    u4 = User(firstname="Daniel", lastname="Patel", email="daniel@example.com", presentation_id=p3.id, activity="Instructor")
    u5 = User(firstname="Ella", lastname="Martinez", email="ella@example.com", presentation_id=p3.id, activity="Assistant")

    db.session.add_all([u1, u2, u3, u4, u5])
    db.session.commit()

    print("Database seeded with test data!")
