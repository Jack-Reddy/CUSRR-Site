# pylint: disable=import-outside-toplevel

'''
Initialize Flask app, database, OAuth, and define routes.
'''
import os
import requests
from flask import Flask, render_template, flash
from flask import session, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from csv_importer import import_users_from_csv

load_dotenv()
db = SQLAlchemy()


def create_app(test_config=None):
    '''
    Generate Flask app instance, register blueprints, and define routes.
    Returns:
        Flask app instance
    '''

    app = Flask(__name__)
    from .config import Config
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    from . import auth

    # Setup app
    app.secret_key = app.config.get('SECRET_KEY') or os.environ.get('FLASK_SECRET')
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
    app.register_blueprint(
        presentations_bp,
        url_prefix='/api/v1/presentations')
    app.register_blueprint(
        block_schedule_bp,
        url_prefix='/api/v1/block-schedule')
    app.register_blueprint(
        abstract_grades_bp,
        url_prefix='/api/v1/abstractgrades')
    app.register_blueprint(grades_bp, url_prefix='/api/v1/grades')

    (auth.organizer_required,
    auth.abstract_grader_required,
    auth.banned_user_redirect,
    auth.presenter_required) = auth.init_role_auth(app, User)

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
        '''
        Render the program page.
        '''
        return render_template('dashboard.html')

    @app.route('/schedule')
    @auth.banned_user_redirect
    def schedule():
        '''
        Render the schedule page.
        Determine if the user is an organizer to show additional features.
        Returns:
            Rendered schedule template with is_organizer flag.
        '''

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
        '''
        Render the fizz-buzz page for banned users.
        '''
        return render_template('fizz-buzz.html')

    @app.route('/dashboard')
    @auth.banned_user_redirect
    def dashboard():
        '''
        Render the dashboard page.
        '''
        return render_template('dashboard.html')

    @app.route('/abstractGrader')
    @auth.banned_user_redirect
    @auth.abstract_grader_required
    def abstract_grader():
        '''
        Render the abstract grader page.
        Permissions: Abstract Grader required.
        '''
        return render_template('abstractGrader.html')

    @app.route('/organizer-user-status')
    @auth.banned_user_redirect
    @auth.organizer_required
    def organizer_user_status():
        '''
        Render the organizer user status page.
        Permissions: Organizer required.
        '''
        return render_template('organizer-user-status.html')

    @app.route('/organizer-presentations-status')
    @auth.banned_user_redirect
    @auth.organizer_required
    def organizer_presentations():
        '''
        Render the organizer presentations status page.
        Permissions: Organizer required.
        '''
        return render_template('organizer-presentations-status.html')

    # Authentication Routes

    @app.route('/google/login')
    def google_login():
        '''
        Initiate Google OAuth login.
        '''
        redirect_uri = url_for('google_auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/google/auth')
    def google_auth():
        '''
        Handle Google OAuth callback and authenticate the user.
        '''
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
                except Exception:
                    # If ID token validation fails, fetch userinfo via OIDC
                    # endpoint
                    if access_token:
                        resp = requests.get(
                            'https://openidconnect.googleapis.com/v1/userinfo',
                            headers={
                                'Authorization': f'Bearer {access_token}'},
                            timeout=10)
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
        except (requests.RequestException, KeyError, ValueError) as e:
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
        # User doesn't exist, redirect to signup page
        return redirect(url_for('signup'))

    @app.route('/google/logout')
    def google_logout():
        '''
        Handle user logout by clearing the session.
        '''
        session.pop('user', None)
        return redirect('/')

    @app.route('/me')
    def me():
        '''
        Return the current user's authentication status and profile information.
        '''
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
        '''
        Render the blitz page.
        '''
        return render_template('blitz_page.html')

    @app.route('/presentation_page')
    def presentation_page():
        '''
        Render the presentation page.
        '''
        return render_template('presentation_page.html')

    @app.route('/poster_page')
    def poster_page():
        '''
        Render the poster page.
        '''
        return render_template('poster_page.html')

    @app.route('/signup')
    def signup():
        '''
        Render the signup page.
        '''
        return render_template('signup.html')

    @app.route('/profile')
    # @presenter_required
    def profile():
        '''
        Render the profile page.
        Permissions: Presenter required.
        '''
        return render_template('profile.html')

    @app.route('/abstract_scoring')
    @auth.abstract_grader_required
    def abstract_scoring():
        '''
        Render the abstract scoring page.
        Permissions: Abstract Grader required.
        '''
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

    if not app.config.get("TESTING", False):
        with app.app_context():
            db.create_all()
    return app


if __name__ == '__main__':
    create_app()
