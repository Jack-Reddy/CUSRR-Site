# pylint: disable=import-outside-toplevel
import os
import requests
from authlib.common.errors import AuthlibBaseError
from flask import Flask, render_template, flash
from flask import session, redirect, url_for, jsonify, request

from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv
from functools import wraps


load_dotenv()
db = SQLAlchemy()


def create_app():

    app = Flask(__name__)
    from .config import Config
    app.config.from_object(Config)
    db.init_app(app)
    from . import auth

    # Setup app
    app.secret_key = os.environ.get('FLASK_SECRET')
    auth.init_oauth(app)
    google = auth.oauth.create_client('google')

    from .models import User, Presentation

    # Routes
    from .routes.users import users_bp
    from .routes.presentations import presentations_bp
    from .routes.block_schedule import block_schedule_bp
    from .routes.abstract_grades import abstract_grades_bp
    from .routes.grades import grades_bp

    # Register API blueprints under `/api/v1/...` so frontend endpoints match
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(presentations_bp, url_prefix='/api/v1/presentations')
    app.register_blueprint(block_schedule_bp, url_prefix='/api/v1/block-schedule')
    app.register_blueprint(abstract_grades_bp, url_prefix='/api/v1/abstractgrades')
    app.register_blueprint(grades_bp, url_prefix='/api/v1/grades')

    auth.init_role_auth(app, db, User)

    @app.route('/import_csv', methods=['POST'])
    @auth.organizer_required
    def import_csv():
        file = request.files.get('csv_file')
        if not file:
            flash("No file selected.", "danger")
            return redirect(url_for('organizer_user_status'))

        if not file.filename.lower().endswith('.csv'):
            flash("File must be a CSV.", "danger")
            return redirect(url_for('organizer_user_status'))

        try:
            added, warnings = import_users_from_csv(file)

            flash(f"Successfully imported {added} users!", "success")

            # Show each warning individually
            for w in warnings:
                flash(w, "warning")

        except (ValueError, IOError) as e:
            flash(f"Error reading CSV: {str(e)}", "danger")

        return redirect(url_for('organizer_user_status'))

    @app.route('/')
    def program():
        return render_template('dashboard.html')

    @app.route('/schedule')
    @auth.banned_user_redirect
    def schedule():

        # if logged in and organizer, pass true
        if 'user' in session:
            user_info = session['user']
            email = user_info.get('email')
            db_user = User.query.filter_by(email=email).first()
            if db_user and db_user.auth == 'organizer':
                return render_template('schedule.html', is_organizer=True)
        return render_template('schedule.html', is_organizer=False)

    @app.route('/fizzbuzz')
    def fizzbuzz():
        return render_template('fizz-buzz.html')

    @app.route('/dashboard')
    @auth.banned_user_redirect
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/abstractGrader')
    @auth.banned_user_redirect
    @auth.abstract_grader_required
    def abstractGrader():
        return render_template('abstractGrader.html')

    @app.route('/organizer-user-status')
    @auth.banned_user_redirect
    @auth.organizer_required
    def organizer_user_status():
        return render_template('organizer-user-status.html')

    @app.route('/organizer-presentations-status')
    @auth.banned_user_redirect
    @auth.organizer_required
    def organizer_presentations():
        return render_template('organizer-presentations-status.html')

    # Authentication Routes

    @app.route('/google/login')
    def google_login():
        redirect_uri = url_for('google_auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/google/auth')
    def google_auth():

        user_info = None

        try:
            code = request.args.get('code')
            if not code:
                raise RuntimeError('missing_authorization_code')

            redirect_uri = url_for('google_auth', _external=True)
            token_resp = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'code': code,
                    'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
                    'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                },
                headers={'Accept': 'application/json'},
                timeout=10
            )
            token_json = token_resp.json()

            access_token = token_json.get('access_token')
            id_token = token_json.get('id_token')

            if id_token:
                try:
                    user_info = google.parse_id_token(
                        token_json,
                        claims_options={
                            'iss': {
                                'values': [
                                    'accounts.google.com',
                                    'https://accounts.google.com']}})
                except (AuthlibBaseError):
                    # If ID token validation fails, fetch userinfo via OIDC
                    # endpoint
                    if access_token:
                        resp = requests.get(
                            'https://openidconnect.googleapis.com/v1/userinfo',
                            headers={'Authorization': f'Bearer {access_token}'},
                            timeout=10
                        )
                        user_info = resp.json()
                    else:
                        user_info = {
                            'error': 'no_access_token_after_id_token_failure',
                            'detail': token_json}
                        
            else:
                if access_token:
                    resp = requests.get(
                        'https://openidconnect.googleapis.com/v1/userinfo',
                        headers={'Authorization': f'Bearer {access_token}'},
                        timeout=10
                    )
                    user_info = resp.json()
                else:
                    user_info = {
                        'error': 'no id_token or access_token',
                        'detail': token_json}
        except (requests.RequestException, AuthlibBaseError, KeyError, ValueError) as e:
            user_info = {
                'error': 'token_exchange_failed',
                'detail': str(e),
                'token_resp': locals().get('token_json')}
        

        session['user'] = user_info
        # Check if user exists in DB
        email = user_info.get('email')
        db_user = User.query.filter_by(email=email).first()

        if db_user:
            # User exists, redirect to dashboard
            return redirect(url_for('dashboard'))
        else:
            # User doesn't exist, redirect to signup page
            return redirect(url_for('signup'))

    @app.route('/google/logout')
    def google_logout():
        session.pop('user', None)
        return redirect('/')

    @app.route('/me')
    def me():
        user = session.get('user')
        if not user:
            return jsonify({'authenticated': False}), 401

        email = user.get('email')
        db_user = User.query.filter_by(
            email=email).first()  # check if account exists

        return jsonify({
            'authenticated': True,
            'name': user.get('name'),
            'email': email,
            'picture': user.get('picture'),
            'account_exists': bool(db_user),  # True if user exists in DB
            'user_id': db_user.id if db_user else None,  # optionally include the DB id
            'auth': db_user.auth if db_user else None,
            'presentation_id': db_user.presentation_id if db_user else None,
            'activity': db_user.activity if db_user else None
        })

    @app.route('/blitz_page')
    def blitz_page():
        return render_template('blitz_page.html')

    @app.route('/presentation_page')
    def presentation_page():
        return render_template('presentation_page.html')

    @app.route('/poster_page')
    def poster_page():
        return render_template('poster_page.html')

    @app.route('/signup')
    def signup():
        return render_template('signup.html')

    @app.route('/profile')
    # @presenter_required
    def profile():
        return render_template('profile.html')

    @app.route('/abstractScoring')
    def abstractScoring():
        # Get presentation
        pres_id = request.args.get("id", type=int)
        presentation = Presentation.query.get_or_404(pres_id)

        # Get current user from session
        user_id = None
        if 'user' in session:
            user_info = session['user']
            email = user_info.get('email')
            db_user = User.query.filter_by(email=email).first()
            if db_user:
                user_id = db_user.id

        return render_template(
            "abstractScoring.html",
            presentation=presentation,
            user_id=user_id  # pass user_id to template
        )


# if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # setup_permissions()
        # After models import
        from .csv_importer import import_users_from_csv
        from .seed import seed_data, setup_permissions
        if User.query.count() == 0:

            seed_data()
    # app.run(debug=True)
    return app


if __name__ == '__main__':
    create_app()
