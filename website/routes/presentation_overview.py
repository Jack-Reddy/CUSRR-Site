"""
Routes for the organizer Program page and program downloads.
"""
import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

from flask import Blueprint, jsonify, render_template, send_file

from website.models import BlockSchedule, Presentation, User
from website.routes.presentations import (
    effective_presentation_time,
    ensure_presentation_metadata_columns,
    get_presentation_type,
    get_show_on_schedule,
    _program_identifier_map,
)

presentation_overview_bp = Blueprint('presentation_overview', __name__)

IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


@presentation_overview_bp.before_request
def ensure_overview_presentation_schema():
    """Keep overview routes compatible with older databases."""
    ensure_presentation_metadata_columns()


def _user_full_name(user):
    """Return a safe full name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


def _format_datetime(value):
    """Format datetimes as naive local ISO strings for JSON."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%dT%H:%M:%S')
    return str(value)


def _format_time(value):
    """Format datetimes for display in the program PDF."""
    if not value:
        return '-'
    try:
        return value.strftime('%b %-d, %Y %-I:%M %p')
    except ValueError:
        return value.strftime('%b %d, %Y %I:%M %p') if hasattr(value, 'strftime') else str(value)


def _visible_presentations():
    """Return visible presentations in program order."""
    presentations = (
        Presentation.query
        .outerjoin(Presentation.schedule)
        .filter(
            (Presentation.schedule_id.is_(None)) |
            (Presentation.schedule.has(is_presentation=True))
        )
        .all()
    )
    presentations = [p for p in presentations if get_show_on_schedule(p.id)]
    presentations.sort(key=lambda p: effective_presentation_time(p) or datetime.max)
    return presentations


def _presenters_for(presentation_id):
    """Return presenter rows for a presentation."""
    return User.query.filter_by(presentation_id=presentation_id).order_by(User.id.asc()).all()


def _overview_list_item(presentation, program_ids):
    """Return the small list payload needed to navigate the Program page."""
    schedule = presentation.schedule
    return {
        'id': presentation.id,
        'title': presentation.title,
        'department': getattr(presentation, 'department', None),
        'mentor': getattr(presentation, 'mentor', None),
        'keywords': getattr(presentation, 'keywords', None),
        'time': _format_datetime(effective_presentation_time(presentation)),
        'type': get_presentation_type(presentation),
        'program_identifier': program_ids.get(presentation.id),
        'schedule_title': schedule.title if schedule else None,
        'show_on_schedule': True,
    }


def _overview_detail_item(presentation, program_ids):
    """Return the detail payload used by the Program page."""
    result = _overview_list_item(presentation, program_ids)
    presenters = _presenters_for(presentation.id)
    result['abstract'] = presentation.abstract
    result['presenters'] = [
        {
            'name': _user_full_name(presenter),
            'email': presenter.email,
        }
        for presenter in presenters
    ]
    return result


def _abstract_for_pdf(abstract):
    """Convert markdown-ish abstract text into safe ReportLab paragraph text."""
    value = abstract or '-'
    value = IMAGE_RE.sub(lambda match: f"[image: {match.group(1) or 'image'}]", value)
    value = re.sub(r'[#*_`$!\[\]()]', '', value)
    return escape(value).replace('\n', '<br/>')


def _append_box(story, label, value, styles, content_width):
    """Append a simple bordered PDF field."""
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch

    table = Table(
        [[Paragraph(f'<b>{escape(label)}:</b> {escape(value or "-")}', styles['BodyText'])]],
        colWidths=[content_width]
    )
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.08 * inch))


def _meal_type_for_block(block):
    """Return lunch/dinner when a non-presentation block is a meal block."""
    marker = f"{block.title or ''} {block.block_type or ''}".lower()
    if 'lunch' in marker:
        return 'lunch'
    if 'dinner' in marker:
        return 'dinner'
    return None


def _program_table_rows(presentations, program_ids):
    """Return simple rows for the program PDF quick-view table."""
    rows = []
    for presentation in presentations:
        presenters = _presenters_for(presentation.id)
        authors = ', '.join(_user_full_name(presenter) for presenter in presenters) or '-'
        display_time = effective_presentation_time(presentation)
        rows.append({
            'sort_time': display_time or datetime.max,
            'time': _format_time(display_time),
            'id': program_ids.get(presentation.id, '-'),
            'authors': authors,
            'title': presentation.title or 'Untitled',
        })

    meal_blocks = BlockSchedule.query.filter(BlockSchedule.is_presentation.is_(False)).all()
    for block in meal_blocks:
        event_type = _meal_type_for_block(block)
        if not event_type:
            continue
        rows.append({
            'sort_time': block.start_time or datetime.max,
            'time': _format_time(block.start_time),
            'id': '',
            'authors': event_type,
            'title': block.title or event_type.title(),
        })

    rows.sort(key=lambda row: (row['sort_time'], row['id'], row['title']))
    for row in rows:
        row.pop('sort_time', None)
    return rows


def _append_program_table(story, styles, content_width, rows):
    """Append the quick-view program table to the PDF."""
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story.append(Paragraph('Program Quick View', styles['Heading1']))
    story.append(Spacer(1, 0.12 * inch))

    if not rows:
        story.append(Paragraph('No program items available.', styles['BodyText']))
        return

    table_data = [[
        Paragraph('<b>Time</b>', styles['Heading5']),
        Paragraph('<b>ID</b>', styles['Heading5']),
        Paragraph('<b>Student Author(s)</b>', styles['Heading5']),
        Paragraph('<b>Title</b>', styles['Heading5']),
    ]]

    for row in rows:
        table_data.append([
            Paragraph(escape(row.get('time') or '-'), styles['BodyText']),
            Paragraph(escape(row.get('id') or ''), styles['BodyText']),
            Paragraph(escape(row.get('authors') or '-'), styles['BodyText']),
            Paragraph(escape(row.get('title') or '-'), styles['BodyText']),
        ])

    table = Table(
        table_data,
        colWidths=[0.95 * inch, 0.75 * inch, 2.0 * inch, content_width - 3.7 * inch],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)


@presentation_overview_bp.route('/overview', methods=['GET'])
def overview():
    """Display the presentation overview page."""
    return render_template('presentation-overview.html')


@presentation_overview_bp.route('/overview/list', methods=['GET'])
def get_presentation_list():
    """Return a lightweight visible-presentation list for the Program page."""
    presentations = _visible_presentations()
    program_ids = _program_identifier_map(presentations)
    return jsonify([
        _overview_list_item(presentation, program_ids)
        for presentation in presentations
    ])


@presentation_overview_bp.route('/overview/all', methods=['GET'])
def get_all_presentations():
    """Return all visible presentations as JSON, ordered by date/time."""
    presentations = _visible_presentations()
    program_ids = _program_identifier_map(presentations)
    return jsonify([
        _overview_detail_item(presentation, program_ids)
        for presentation in presentations
    ])


@presentation_overview_bp.route('/overview/download.pdf', methods=['GET'])
def download_overview_pdf():
    """Download the visible program as a PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    presentations = _visible_presentations()
    program_ids = _program_identifier_map(presentations)
    rows = _program_table_rows(presentations, program_ids)

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

    _append_program_table(story, styles, content_width, rows)

    if presentations:
        story.append(PageBreak())
        for index, presentation in enumerate(presentations):
            presenters = _presenters_for(presentation.id)
            authors = ', '.join(_user_full_name(presenter) for presenter in presenters) or '-'
            display_time = _format_time(effective_presentation_time(presentation))
            program_id = program_ids.get(presentation.id, '-')

            story.append(Paragraph('Program Entry', styles['Heading1']))
            story.append(Spacer(1, 0.08 * inch))
            _append_box(story, 'Program ID', program_id, styles, content_width)
            _append_box(story, 'Title', presentation.title or 'Untitled', styles, content_width)
            _append_box(story, 'Date/Time', display_time, styles, content_width)
            _append_box(story, 'Author(s)', authors, styles, content_width)
            _append_box(story, 'Department', getattr(presentation, 'department', None) or '-', styles, content_width)
            _append_box(story, 'Mentor', getattr(presentation, 'mentor', None) or '-', styles, content_width)
            _append_box(story, 'Keywords', getattr(presentation, 'keywords', None) or '-', styles, content_width)

            story.append(Paragraph('<b>Abstract</b>', styles['Heading2']))
            story.append(Paragraph(_abstract_for_pdf(presentation.abstract), styles['BodyText']))

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
    """Return a single visible presentation with presenter details."""
    presentation = Presentation.query.get_or_404(presentation_id)
    if not get_show_on_schedule(presentation.id):
        return jsonify({'error': 'Presentation hidden'}), 404

    presentations = _visible_presentations()
    if presentation.id not in {item.id for item in presentations}:
        presentations.append(presentation)
    program_ids = _program_identifier_map(presentations)

    return jsonify(_overview_detail_item(presentation, program_ids))
