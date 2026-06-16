"""
Routes for presentation overview page.
"""
import base64
import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

import requests
from flask import Blueprint, current_app, render_template, jsonify, send_file
from sqlalchemy import text

from website import db
from website.models import Presentation, User
from website.routes.presentations import (
    effective_presentation_time,
    get_show_on_schedule,
    presentation_to_dict,
    program_table_rows,
)

presentation_overview_bp = Blueprint('presentation_overview', __name__)

IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


def _user_full_name(user):
    """Return a safe full name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


def _visible_presentations():
    presentations = [
        p for p in Presentation.query.order_by(Presentation.id.asc()).all()
        if get_show_on_schedule(p.id)
    ]
    presentations.sort(key=lambda p: effective_presentation_time(p) or datetime.max)
    return presentations


def _format_time(value):
    if not value:
        return '-'
    try:
        return value.strftime('%b %-d, %Y %-I:%M %p')
    except ValueError:
        return value.strftime('%b %d, %Y %I:%M %p') if hasattr(value, 'strftime') else str(value)


@presentation_overview_bp.route('/overview', methods=['GET'])
def overview():
    """Display the presentation overview page."""
    return render_template('presentation-overview.html')


@presentation_overview_bp.route('/overview/all', methods=['GET'])
def get_all_presentations():
    """
    Return all visible presentations as JSON, ordered by date/time.
    Used by the front-end for navigation.
    """
    presentations = (
        Presentation.query
        .outerjoin(Presentation.schedule)
        .filter(
            (Presentation.schedule_id.is_(None)) | (Presentation.schedule.has(is_presentation=True))
        )
        .all()
    )
    presentations = [p for p in presentations if get_show_on_schedule(p.id)]
    presentations.sort(key=lambda p: effective_presentation_time(p) or datetime.max)
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
                max_width = 6.2 * inch
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


def _box(flowables, width):
    """Wrap PDF flowables in a black bordered box."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table([[flowables]], colWidths=[width])
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return table


def _append_program_table_to_story(story, styles, content_width):
    """Add the program quick-view table as the first PDF page."""
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    rows = program_table_rows()
    story.append(Paragraph('Program Quick View', styles['Heading1']))
    story.append(Spacer(1, 0.12 * inch))

    if not rows:
        story.append(Paragraph('No program items available.', styles['BodyText']))
        return

    header_style = styles['Heading5']
    body_style = styles['BodyText']
    table_data = [[
        Paragraph('<b>Time</b>', header_style),
        Paragraph('<b>ID</b>', header_style),
        Paragraph('<b>Student Author(s)</b>', header_style),
        Paragraph('<b>Title</b>', header_style),
    ]]
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    for row in rows:
        table_row = [
            Paragraph(escape(row.get('time') or '-'), body_style),
            Paragraph(escape(row.get('id') or ''), body_style),
            Paragraph(escape(row.get('authors') or '-'), body_style),
            Paragraph(escape(row.get('title') or '-'), body_style),
        ]
        table_data.append(table_row)
        if row.get('kind') == 'event' and row.get('event_type') in ('lunch', 'dinner'):
            row_index = len(table_data) - 1
            table_style.append(
                ('BACKGROUND', (2, row_index), (2, row_index), colors.HexColor('#cfe2ff'))
            )
            table_style.append(
                ('TEXTCOLOR', (2, row_index), (2, row_index), colors.HexColor('#084298'))
            )

    table = Table(
        table_data,
        colWidths=[0.95 * inch, 0.75 * inch, 2.0 * inch, content_width - 3.7 * inch],
        repeatRows=1,
    )
    table.setStyle(TableStyle(table_style))
    story.append(table)


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
    content_width = 7.2 * inch
    story = []

    _append_program_table_to_story(story, styles, content_width)

    if presentations:
        story.append(PageBreak())
        for index, presentation in enumerate(presentations):
            presenters = User.query.filter_by(presentation_id=presentation.id).all()
            authors = ', '.join([_user_full_name(p) for p in presenters]) or '-'
            activities = sorted(
                {p.activity.strip() for p in presenters if p.activity and p.activity.strip()}
            )
            activity_text = ', '.join(activities) if activities else '-'
            display_time = _format_time(effective_presentation_time(presentation))
            presentation_data = presentation_to_dict(presentation)
            program_id = presentation_data.get('program_identifier') or '-'

            story.append(_box([Paragraph(f'<b>Program ID:</b> {escape(program_id)}', styles['BodyText'])], content_width))
            story.append(Spacer(1, 0.08 * inch))
            story.append(_box([Paragraph(escape(presentation.title or 'Untitled'), styles['Heading1'])], content_width))
            story.append(Spacer(1, 0.08 * inch))
            story.append(_box([Paragraph(f'<b>Date/Time:</b> {escape(display_time)}', styles['BodyText'])], content_width))
            story.append(Spacer(1, 0.08 * inch))
            story.append(_box([Paragraph(f'<b>Author(s):</b> {escape(authors)}', styles['BodyText'])], content_width))
            story.append(Spacer(1, 0.08 * inch))
            story.append(_box([Paragraph(f'<b>Activity:</b> {escape(activity_text)}', styles['BodyText'])], content_width))
            story.append(Spacer(1, 0.08 * inch))
            abstract_flowables = [Paragraph('<b>Abstract</b>', styles['Heading2'])]
            _append_markdown_to_story(abstract_flowables, presentation.abstract or '-', styles)
            story.append(_box(abstract_flowables, content_width))

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
            'activity': p.activity,
        }
        for p in presenters
    ]

    result = presentation_to_dict(presentation)
    result['presenters'] = presenters_info

    return jsonify(result)
