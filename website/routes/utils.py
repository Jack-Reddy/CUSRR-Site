'''Collection of utility functions for the website routes.
'''

from flask import jsonify
from website.models import Presentation
from website import db


def format_average_grades(averages):
    ''' Format average grades with presentation titles '''
    results = []
    for avg in averages:
        presentation = db.session.get(Presentation, avg.presentation_id)

        results.append({
            "presentation_id": avg.presentation_id,
            "presentation_title": presentation.title if presentation else None,
            "average_score": round(avg.average_score, 2),
            "num_grades": avg.num_grades
        })
    return jsonify(results)
