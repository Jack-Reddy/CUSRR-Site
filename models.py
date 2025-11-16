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
    grades = db.relationship('Grade', back_populates='presentation', cascade='all, delete')
    abstract_grades = db.relationship('AbstractGrade', back_populates='presentation', cascade='all, delete')

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
    auth = db.Column(db.String(80), default='organizer')

    # Relationship to Presentation
    presentation = db.relationship('Presentation', back_populates='presenters')
    grades_given = db.relationship('Grade', back_populates='grader', cascade='all, delete')
    abstract_grades_given = db.relationship('AbstractGrade', back_populates='grader', cascade='all, delete')

    

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
            "auth": self.auth
        }

    def to_dict_basic(self):
        return {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "email": self.email
        }

class Grade(db.Model):
    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('presentations.id'), nullable=False)

    criteria_1 = db.Column(db.Integer, nullable=False)
    criteria_2 = db.Column(db.Integer, nullable=False)
    criteria_3 = db.Column(db.Integer, nullable=False)

    grader = db.relationship('User', back_populates='grades_given')
    presentation = db.relationship('Presentation', back_populates='grades')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "grader_name": f"{self.grader.firstname} {self.grader.lastname}" if self.grader else None,
            "presentation_id": self.presentation_id,
            "presentation_title": self.presentation.title if self.presentation else None,
            "criteria_1": self.criteria_1,
            "criteria_2": self.criteria_2,
            "criteria_3": self.criteria_3,
        }


class AbstractGrade(db.Model):
    __tablename__ = "abstract_grades"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('presentations.id'), nullable=False)

    criteria_1 = db.Column(db.Float, nullable=False)
    criteria_2 = db.Column(db.Float, nullable=False)
    criteria_3 = db.Column(db.Float, nullable=False)

    grader = db.relationship('User', back_populates='abstract_grades_given')
    presentation = db.relationship('Presentation', back_populates='abstract_grades')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "grader_name": f"{self.grader.firstname} {self.grader.lastname}" if self.grader else None,
            "presentation_id": self.presentation_id,
            "presentation_title": self.presentation.title if self.presentation else None,
            "criteria_1": self.criteria_1,
            "criteria_2": self.criteria_2,
            "criteria_3": self.criteria_3,
        }