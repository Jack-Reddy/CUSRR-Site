from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import timedelta, datetime
from website import db

# db = SQLAlchemy()

class Presentation(db.Model):
    __tablename__ = "presentations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    abstract = db.Column(db.Text)
    subject = db.Column(db.String(100))
    time = db.Column(DateTime)
    num_in_block = db.Column(db.Integer) # New field to track number of presentations in the same block
    schedule_id = db.Column(db.Integer, db.ForeignKey('blockSchedules.id'))

    presenters = db.relationship('User', back_populates='presentation')
    grades = db.relationship('Grade', back_populates='presentation', cascade='all, delete')
    abstract_grades = db.relationship('AbstractGrade', back_populates='presentation', cascade='all, delete')
    schedule = db.relationship('BlockSchedule', back_populates='presentations')

    def to_dict(self):
        calculated_time = None
        if self.time:
            calculated_time = self.time
        elif self.schedule:
            if self.num_in_block is not None and self.schedule.sub_length is not None:
                calculated_time = self.schedule.start_time + timedelta(minutes=self.num_in_block * self.schedule.sub_length)
            else:
                calculated_time = self.schedule.start_time
        # Format datetimes as naive local ISO strings (no timezone suffix)
        def fmt(dt):
            if not dt:
                return None
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%dT%H:%M:%S')
            return str(dt)

        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "subject": self.subject,
            "time": fmt(calculated_time),
            "room": self.schedule.location if self.schedule else None,
            "type": self.schedule.block_type if self.schedule else None,
            "num_in_block": self.num_in_block,
            "presenters": [p.to_dict_basic() for p in self.presenters],
            "schedule_id": self.schedule_id
        }

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('presentations.id'))
    activity = db.Column(db.String(80))
    auth = db.Column(db.String(80), default='attendee')

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

class BlockSchedule(db.Model):
    __tablename__ = "blockSchedules"

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(DateTime, nullable=False)
    end_time = db.Column(DateTime, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    location = db.Column(db.String(100))
    block_type = db.Column(db.String(50))
    sub_length = db.Column(db.Integer)

    presentations = db.relationship('Presentation', back_populates='schedule', cascade='save-update')

    def to_dict(self):
        return {
            "id": self.id,
            "day": self.day,
            "startTime": self.start_time.strftime('%Y-%m-%dT%H:%M:%S') if self.start_time else None,
            "endTime": self.end_time.strftime('%Y-%m-%dT%H:%M:%S') if self.end_time else None,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "length": (self.end_time - self.start_time).total_seconds() / 60,
            "type": self.block_type,
            "sub_length": self.sub_length
        }