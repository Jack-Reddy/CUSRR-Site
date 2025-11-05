from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Presentation(db.Model):
    __tablename__ = "presentations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    abstract = db.Column(db.String(500))
    subject = db.Column(db.String(100))
    time = db.Column(db.String(50))
    room = db.Column(db.String(50))
    type = db.Column(db.String(50))

    presenters = db.relationship('User', back_populates='presentation', cascade='all, delete')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "subject": self.subject,
            "time": self.time,
            "room": self.room,
            "type": self.type,
            "presenters": [p.to_dict_basic() for p in self.presenters]
        }

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('presentations.id'))
    activity = db.Column(db.String(80))

    # Relationship to Presentation
    presentation = db.relationship('Presentation', back_populates='presenters')

    def to_dict(self):
        return {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "name": f"{self.firstname} {self.lastname}",
            "email": self.email,
            "activity": self.activity,
            "presentation": self.presentation.title if self.presentation else None,
            "presentation_id" : self.presentation_id,
            "status": "Registered"  # Placeholder for user status
        }

    def to_dict_basic(self):
        return {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "email": self.email
        }
