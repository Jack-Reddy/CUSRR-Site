"""
Routes for presentation overview page.
"""
import base64
import io
import re
import textwrap
from xml.sax.saxutils import escape

import requests
from flask import Blueprint, current_app, render_template, jsonify, send_file
from sqlalchemy import text

from website import db
from website.models import Presentation, User
from website.routes.presentations import get_show_on_schedule, presentation_to_dict

presentation_overview_bp = Blueprint('presentation_overview', __name__)

IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


def _user_full_name(user):
    """Return a safe full name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


def _visible_presentations():
    return [
        p for p in Presentation.query.order_by(Presentation.id.asc()).all()
        if get_show_on_schedule(p.id)
    ]


@presentation_overview_bp.route('/overview', methods=['GET'])
def overview():
    """Display the presentation overview page."""
    return render_template('presentation-overview.html')


@presentation_overview_bp.route('/overview/all', methods=['GET'])
def get_all_presentations():
    """
    Return all visible presentations as JSON, ordered by ID.
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
    presentations = [p for p in presentations if get_show_on_schedule(p.id)]
    return jsonify([presentation_to_dict(p) for p in presentations])


def _markdown_inline_to_reportlab(text):
    value = escape(text or '')
    value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value)
    value = re.sub(r'__(.+?)__', r'<b>\1</b>', value)
    value = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', value)
    value = re.sub(r'_([^_]+?)_', r'<i>\1</i>', value)
    value = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', value)
    return value.replace('\n', '<br/>')


def _image_bytes_from_url(url):
    if not url:
        return None

    if url.startswith('/api/v1/presentations/abstract-images/'):
        image_id = url.rstrip('/').split('/')[-1]
        row = db.session.execute(
            text('SELECT data_base64 FROM abstract_images WHERE id = :id'),
            {'id': image_id}
        ).fetchone()
        if row:
            return base64.b64decode(row[0])
        return None

    if url.startswith('/static/'):
        static_path = url[len('/static/'):]
        file_path = current_app.root_path + '/static/' + static_path
        try:
            with open(file_path, 'rb') as image_file:
                return image_file.read()
        except OSError:
            return None

    if url.startswith('http://') or url.startswith('https://'):
        try:
            response = requests.get(url, timeout=5)
            if response.ok and response.content:
                return response.content
        except requests.RequestException:
            return None

    return None


def _append_markdown_to_story(story, abstract, styles):
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, Spacer

    body_style = styles['BodyText']
    body_style.leading = 14

    def add_text_block(text_block):
        for block in re.split(r'\n\s*\n', text_block or ''):
            block = block.strip()
            if not block:
                continue
            if block.startswith('#'):
                block = block.lstrip('#').strip()
                story.append(Paragraph(_markdown_inline_to_reportlab(block), styles['Heading3']))
            else:
                story.append(Paragraph(_markdown_inline_to_reportlab(block), body_style))
            story.append(Spacer(1, 0.08 * inch))

    position = 0
    for match in IMAGE_RE.finditer(abstract or ''):
        add_text_block((abstract or '')[position:match.start()])
        alt_text = match.group(1) or 'image'
        image_url = match.group(2)
        image_data = _image_bytes_from_url(image_url)
        if image_data:
            try:
                image = Image(io.BytesIO(image_data))
                max_width = 6.5 * inch
                max_height = 3.5 * inch
                scale = min(max_width / image.imageWidth, max_height / image.imageHeight, 1)
                image.drawWidth = image.imageWidth * scale
                image.drawHeight = image.imageHeight * scale
                image.hAlign = 'LEFT'
                story.append(image)
                story.append(Spacer(1, 0.12 * inch))
            except Exception:
                story.append(Paragraph(f'[image unavailable: {escape(alt_text)}]', body_style))
        else:
            story.append(Paragraph(f'[image unavailable: {escape(alt_text)}]', body_style))
        position = match.end()

    add_text_block((abstract or '')[position:])


@presentation_overview_bp.route('/overview/download.pdf', methods=['GET'])
def download_overview_pdf():
    """Download the full visible program as one PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    presentations = _visible_presentations()
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )
    styles = getSampleStyleSheet()
    story = [Paragraph('CUSRR Program', styles['Title']), Spacer(1, 0.25 * inch)]

    if not presentations:
        story.append(Paragraph('No presentations available.', styles['BodyText']))
    else:
        for index, presentation in enumerate(presentations):
            presenters = User.query.filter_by(presentation_id=presentation.id).all()
            authors = ', '.join([_user_full_name(p) for p in presenters]) or '-'
            departments = sorted(
                {p.activity.strip() for p in presenters if p.activity and p.activity.strip()}
            )
            department_text = ', '.join(departments) if departments else '-'

            story.append(Paragraph(escape(presentation.title or 'Untitled'), styles['Heading1']))
            story.append(Paragraph(f'<b>Session ID:</b> {presentation.id}', styles['BodyText']))
            story.append(Paragraph(f'<b>Author(s):</b> {escape(authors)}', styles['BodyText']))
            story.append(Paragraph(f'<b>Department:</b> {escape(department_text)}', styles['BodyText']))
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph('<b>Abstract</b>', styles['Heading2']))
            _append_markdown_to_story(story, presentation.abstract or '-', styles)

            if index < len(presentations) - 1:
                story.append(PageBreak())

    doc.build(story)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='cusrr_program.pdf',
    )


@presentation_overview_bp.route('/overview/<int:presentation_id>', methods=['GET'])
def get_presentation_detail(presentation_id):
    """
    Return a single visible presentation with its presenter details.
    """
    presentation = Presentation.query.get_or_404(presentation_id)
    if not get_show_on_schedule(presentation.id):
        return jsonify({"error": "Presentation hidden"}), 404

    presenters = User.query.filter_by(presentation_id=presentation_id).all()
    presenters_info = [
        {
            'name': _user_full_name(p),
            'email': p.email,
            'department': p.activity,
        }
        for p in presenters
    ]

    result = presentation_to_dict(presentation)
    result['presenters'] = presenters_info

    return jsonify(result)
