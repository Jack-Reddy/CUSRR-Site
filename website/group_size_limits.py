"""Group-size limits shared by presentation creation and attendee assignment."""
from datetime import datetime

from flask import jsonify, request

from website import db
from website.models import Presentation, User
from website.routes import presentations as presentations_module
from website.routes import users as users_module

MAX_PRESENTERS_PER_GROUP = 5


def _can_assign_presentation_with_five_person_limit(user, presentation_id):
    """Assign a user to a presentation while allowing five presenters total."""
    if presentation_id in (None, ''):
        user.presentation_id = None
        return None

    try:
        presentation_id = int(presentation_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid presentation_id"}), 400

    presentation = db.session.get(Presentation, presentation_id)
    if not presentation:
        return jsonify({"error": "Presentation not found"}), 404

    existing_presenters = User.query.filter(
        User.presentation_id == presentation.id,
        User.id != user.id
    ).count()
    if existing_presenters >= MAX_PRESENTERS_PER_GROUP:
        return jsonify({"error": f"Presentation already has {MAX_PRESENTERS_PER_GROUP} presenters"}), 403

    user.presentation_id = presentation.id
    return None


def create_presentation_with_five_person_limit():
    """Create a presentation while allowing up to five presenters total."""
    data = request.get_json() or {}
    schedule_id = data.get('schedule_id') or data.get('block_id')
    time_str = data.get('time')

    parsed_time = None
    if time_str:
        try:
            parsed_time = datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400

    partner_emails = data.get('partner_emails') or []
    legacy_partner_email = data.get('partner_email')
    if legacy_partner_email and legacy_partner_email not in partner_emails:
        partner_emails.append(legacy_partner_email)
    partner_emails = [email.strip() for email in partner_emails if email and email.strip()]
    partner_emails = list(dict.fromkeys(partner_emails))

    if len(partner_emails) > MAX_PRESENTERS_PER_GROUP - 1:
        return jsonify({"error": f"Groups can have at most {MAX_PRESENTERS_PER_GROUP} presenters total"}), 400

    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        department=presentations_module._clean_text(data.get('department')),
        mentor=presentations_module._clean_text(data.get('mentor')),
        keywords=presentations_module._clean_text(data.get('keywords')),
        time=parsed_time,
        schedule_id=schedule_id
    )

    db.session.add(new_presentation)
    db.session.flush()
    presentations_module.set_show_on_schedule(new_presentation.id, data.get('show_on_schedule', True))
    if 'type' in data:
        presentations_module.set_presentation_type(new_presentation.id, data.get('type'))

    for partner_email in partner_emails:
        partner_user = User.query.filter_by(email=partner_email).first()
        if not partner_user:
            db.session.rollback()
            return jsonify({"error": f"No user found with email {partner_email}"}), 400
        if partner_user.presentation_id:
            db.session.rollback()
            return jsonify({"error": f"{partner_email} is already assigned to a presentation"}), 400
        partner_user.presentation_id = new_presentation.id

    db.session.commit()
    return jsonify(presentations_module.presentation_to_dict(new_presentation)), 201


def install_group_size_limit_overrides(app):
    """Install five-person group-size behavior before the API blueprints are registered."""
    users_module._can_assign_presentation = _can_assign_presentation_with_five_person_limit
    app.add_url_rule(
        '/api/v1/presentations/',
        'create_presentation_with_five_person_limit',
        create_presentation_with_five_person_limit,
        methods=['POST']
    )
