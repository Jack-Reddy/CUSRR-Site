"""
Routes for presentation overview page.
"""
import base64
import io
import re
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

import requests
from flask import Blueprint, current_app, render_template, jsonify, send_file
from sqlalchemy import text

from website import db
from website.models import BlockSchedule, Presentation, User
from website.routes.presentations import (
    effective_presentation_time,
    get_presentation_type,
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


def _presentation_color(presentation, fallback_index=0):
    """Return the PDF color for the presentation's program type."""
    from reportlab.lib import colors

    presentation_type = (get_presentation_type(presentation) or '').strip().lower()
    if presentation_type == 'poster':
        return colors.HexColor('#f4b183')
    if presentation_type == 'blitz':
        return colors.HexColor('#e06666')
    if presentation_type == 'presentation':
        return colors.HexColor('#93c47d')
    return colors.HexColor('#ffd966') if fallback_index % 2 == 0 else colors.HexColor('#9fc5e8')


def _block_color(index=0):
    """Return alternating color for non-presentation schedule blocks."""
    from reportlab.lib import colors

    return colors.HexColor('#ffd966') if index % 2 == 0 else colors.HexColor('#9fc5e8')


def _short_pdf_time(value):
    if not value:
        return '-'
    try:
        return value.strftime('%-I:%M %p')
    except ValueError:
        return value.strftime('%I:%M %p')


def _schedule_duration_minutes(start, end, fallback=30):
    if start and end and end > start:
        return max(1, int((end - start).total_seconds() / 60))
    return fallback


def _visual_schedule_items():
    """Build visual schedule items from schedule blocks and visible presentations."""
    schedule_blocks = BlockSchedule.query.order_by(BlockSchedule.start_time.asc()).all()
    visible_presentations = {
        presentation.id: presentation
        for presentation in _visible_presentations()
    }
    items = []
    other_index = 0

    for block in schedule_blocks:
        if not block.start_time:
            continue

        block_end = block.end_time or block.start_time + timedelta(minutes=60)
        if block.is_presentation:
            block_presentations = [
                presentation
                for presentation in block.presentations
                if presentation.id in visible_presentations
            ]
            block_presentations.sort(
                key=lambda presentation: (
                    effective_presentation_time(presentation) or block.start_time,
                    presentation.num_in_block if presentation.num_in_block is not None else 10**9,
                    presentation.id or 0,
                )
            )

            if not block_presentations:
                items.append({
                    'start': block.start_time,
                    'end': block_end,
                    'title': block.title or 'Presentation Block',
                    'subtitle': block.location or '',
                    'color': _block_color(other_index),
                })
                other_index += 1
                continue

            fallback_duration = max(
                1,
                int(_schedule_duration_minutes(block.start_time, block_end) / max(len(block_presentations), 1))
            )
            for presentation in block_presentations:
                start = effective_presentation_time(presentation) or block.start_time
                minutes = block.sub_length or fallback_duration
                end = min(start + timedelta(minutes=minutes), block_end)
                if end <= start:
                    end = start + timedelta(minutes=minutes)
                program_id = presentation_to_dict(presentation).get('program_identifier') or ''
                items.append({
                    'start': start,
                    'end': end,
                    'title': presentation.title or 'Untitled',
                    'subtitle': program_id,
                    'color': _presentation_color(presentation),
                })
        else:
            items.append({
                'start': block.start_time,
                'end': block_end,
                'title': block.title or 'Schedule Block',
                'subtitle': block.location or (block.block_type or ''),
                'color': _block_color(other_index),
            })
            other_index += 1

    if items:
        return sorted(items, key=lambda item: (item['start'], item['end'], item['title']))

    return []


class _VisualScheduleFlowable:
    """ReportLab-compatible object that draws a time-scaled vertical program schedule."""

    def __init__(self, items, width, height):
        self.items = items
        self.width = width
        self.height = height
        self._fixedWidth = 1
        self._fixedHeight = 1

    def getKeepWithNext(self):
        return 0

    def getSpaceAfter(self):
        return 0

    def getSpaceBefore(self):
        return 0

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def split(self, available_width, available_height):
        return []

    def drawOn(self, canvas, x, y, _sW=0):
        from reportlab.lib import colors
        from reportlab.pdfbase.pdfmetrics import stringWidth

        if not self.items:
            canvas.setFont('Helvetica', 10)
            canvas.drawString(x, y + self.height - 14, 'No schedule items available.')
            return

        day_start = min(item['start'] for item in self.items)
        day_end = max(item['end'] for item in self.items)
        if day_end <= day_start:
            day_end = day_start + timedelta(minutes=60)

        total_minutes = max(1, int((day_end - day_start).total_seconds() / 60))
        axis_width = 0.72 * 72
        gutter = 0.12 * 72
        block_x = x + axis_width + gutter
        block_width = self.width - axis_width - gutter
        top_padding = 0.12 * 72
        bottom_padding = 0.12 * 72
        plot_height = self.height - top_padding - bottom_padding
        plot_top = y + self.height - top_padding
        plot_bottom = y + bottom_padding

        def y_for_time(value):
            minutes = (value - day_start).total_seconds() / 60
            return plot_top - (minutes / total_minutes) * plot_height

        canvas.setStrokeColor(colors.HexColor('#b7b7b7'))
        canvas.setLineWidth(0.5)
        canvas.line(x + axis_width, plot_bottom, x + axis_width, plot_top)

        tick = day_start.replace(minute=0, second=0, microsecond=0)
        if tick < day_start:
            tick += timedelta(hours=1)
        while tick <= day_end:
            tick_y = y_for_time(tick)
            canvas.setStrokeColor(colors.HexColor('#dddddd'))
            canvas.line(block_x, tick_y, block_x + block_width, tick_y)
            canvas.setFillColor(colors.HexColor('#333333'))
            canvas.setFont('Helvetica', 7)
            canvas.drawRightString(x + axis_width - 4, tick_y - 2, _short_pdf_time(tick))
            tick += timedelta(hours=1)

        for item in self.items:
            top = y_for_time(item['start'])
            bottom = y_for_time(item['end'])
            rect_y = min(top, bottom)
            rect_height = max(10, abs(top - bottom) - 2)

            canvas.setFillColor(item['color'])
            canvas.setStrokeColor(colors.HexColor('#666666'))
            canvas.rect(block_x, rect_y, block_width, rect_height, stroke=1, fill=1)

            text_x = block_x + 5
            text_y = rect_y + rect_height - 9
            canvas.setFillColor(colors.black)
            canvas.setFont('Helvetica-Bold', 7)
            title = item['title'] or 'Schedule Item'
            max_text_width = block_width - 10
            while title and stringWidth(title + '...', 'Helvetica-Bold', 7) > max_text_width:
                title = title[:-1]
            if title != (item['title'] or 'Schedule Item'):
                title = title.rstrip() + '...'
            canvas.drawString(text_x, text_y, title)

            if rect_height >= 20:
                subtitle = item.get('subtitle') or f"{_short_pdf_time(item['start'])} - {_short_pdf_time(item['end'])}"
                canvas.setFont('Helvetica', 6.5)
                while subtitle and stringWidth(subtitle + '...', 'Helvetica', 6.5) > max_text_width:
                    subtitle = subtitle[:-1]
                if subtitle != (item.get('subtitle') or f"{_short_pdf_time(item['start'])} - {_short_pdf_time(item['end'])}"):
                    subtitle = subtitle.rstrip() + '...'
                canvas.drawString(text_x, text_y - 8, subtitle)


def _append_visual_schedule_to_story(story, styles, content_width):
    """Add a visual, time-scaled schedule page to the program PDF."""
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer

    story.append(Paragraph('Visual Schedule', styles['Heading1']))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_VisualScheduleFlowable(_visual_schedule_items(), content_width, 6.85 * inch))


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
    story.append(PageBreak())
    _append_visual_schedule_to_story(story, styles, content_width)

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
