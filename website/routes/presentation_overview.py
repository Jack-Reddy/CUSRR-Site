"""
Routes for presentation overview page.
"""
import io
import textwrap

from flask import Blueprint, render_template, jsonify, send_file

from website.models import Presentation, User

presentation_overview_bp = Blueprint('presentation_overview', __name__)


def _user_full_name(user):
    """Return a safe full name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


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
    presentations = (
        Presentation.query
        .outerjoin(Presentation.schedule)
        .filter(
            (Presentation.schedule_id.is_(None)) | (Presentation.schedule.has(is_presentation=True))
        )
        .order_by(Presentation.id.asc())
        .all()
    )
    return jsonify([p.to_dict() for p in presentations])


@presentation_overview_bp.route('/overview/download.pdf', methods=['GET'])
def download_overview_pdf():
    """Download a PDF with all presentation overviews (one per page)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    presentations = Presentation.query.order_by(Presentation.id.asc()).all()

    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    margin_x = 50
    box_width = width - (2 * margin_x)
    y_cursor = height - 50

    def draw_box(label, value):
        nonlocal y_cursor
        label_text = f"{label}:"
        value_text = str(value or '-')

        wrapped = textwrap.wrap(value_text, width=90) or ['-']
        line_height = 14
        box_height = 26 + (len(wrapped) * line_height)

        # Always create a new page if we don't have enough space
        if y_cursor - box_height < 45:
            pdf.showPage()
            y_cursor = height - 50

        y_top = y_cursor
        y_bottom = y_cursor - box_height

        pdf.setLineWidth(1)
        pdf.rect(margin_x, y_bottom, box_width, box_height)

        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(margin_x + 10, y_top - 18, label_text)

        pdf.setFont('Helvetica', 10)
        text_y = y_top - 34
        for line in wrapped:
            pdf.drawString(margin_x + 10, text_y, line)
            text_y -= line_height

        y_cursor = y_bottom - 10

    for index, presentation in enumerate(presentations, start=1):
        # Start each presentation on a new page
        if index > 1:
            pdf.showPage()
            y_cursor = height - 50

        presenters = User.query.filter_by(presentation_id=presentation.id).all()
        authors = ', '.join([_user_full_name(p) for p in presenters]) or '-'

        departments = sorted(
            {p.activity.strip() for p in presenters if p.activity and p.activity.strip()}
        )
        department_text = ', '.join(departments) if departments else '-'

        draw_box('Session ID', presentation.id)
        draw_box('Abstract Title', presentation.title)
        draw_box('Author(s)', authors)
        draw_box('Department', department_text)
        draw_box('Abstract', presentation.abstract or '-')

    if not presentations:
        pdf.setFont('Helvetica', 12)
        pdf.drawString(margin_x, height - 70, 'No presentations available.')

    pdf.save()
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='presentation_overviews.pdf',
    )


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
            'name': _user_full_name(p),
            'email': p.email,
            'department': p.activity,
        }
        for p in presenters
    ]

    result = presentation.to_dict()
    result['presenters'] = presenters_info

    return jsonify(result)
