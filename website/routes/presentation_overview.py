"""
Routes for presentation overview page.
"""
from flask import Blueprint, render_template, jsonify, request
from website.models import Presentation, User

presentation_overview_bp = Blueprint('presentation_overview', __name__)


@presentation_overview_bp.route('/overview', methods=['GET'])
def overview():
    """Display the presentation overview page."""
    return render_template('presentation-overview.html')


@presentation_overview_bp.route('/overview/all', methods=['GET'])
def get_all_presentations():
    """
    Return all presentations as JSON, ordered by ID.
    Used by the front-end for navigation.
    """
    presentations = Presentation.query.order_by(Presentation.id.asc()).all()
    return jsonify([p.to_dict() for p in presentations])


@presentation_overview_bp.route('/overview/<int:presentation_id>', methods=['GET'])
def get_presentation_detail(presentation_id):
    """
    Return a single presentation with its presenter details.
    """
    presentation = Presentation.query.get_or_404(presentation_id)

    # Get all presenters for this presentation
    presenters = User.query.filter_by(presentation_id=presentation_id).all()
    presenters_info = [
        {
            'name': p.name,
            'email': p.email,
            'department': p.department,
        }
        for p in presenters
    ]

    result = presentation.to_dict()
    result['presenters'] = presenters_info

    return jsonify(result)
