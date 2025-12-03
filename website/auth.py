
'''
Authentication and role-based authorization for the Flask app.
Uses OAuth2 with Google as the identity provider.
'''
from functools import wraps
import os
from authlib.integrations.flask_client import OAuth
from flask import session, redirect, url_for, jsonify, request

oauth = OAuth()


def init_oauth(app):
    '''
    Initialize OAuth with Google as the identity provider.
    Parameters: app - Flask application instance
    '''
    if not getattr(app, 'secret_key', None):
        app.secret_key = os.environ.get('APP_SECRET_KEY')

    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),

        # API endpoints
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,

        # metadata (use Google's OpenID Connect discovery so Authlib can
        # retrieve jwks_uri and other metadata required for OIDC)
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',

        # login page
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,

        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'openid email profile'},
    )


def init_role_auth(app, db, user):
    '''
    Initialize role-based authorization decorators.
    Parameters:
        app - Flask application instance
        db - SQLAlchemy database instance
        User - User model class
    Returns:
        Tuple of decorators:
        (organizer_required, abstract_grader_required,
         banned_user_redirect, presenter_required)
    '''

    def organizer_required(view):
        '''
        Decorator to require organizer role for a view.
        Redirects to login/signup if not authenticated.
        Returns 403 JSON error for AJAX requests if not authorized.
        '''
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_info = session.get('user')
            if not user_info:
                return redirect(url_for('google_login'))

            email = user_info.get('email')
            if not email:
                return redirect(url_for('google_login'))

            db_user = user.query.filter_by(email=email).first()
            if not db_user:
                return redirect(url_for('signup'))

            if db_user.auth == 'organizer':
                return view(*args, **kwargs)

            wants_json = request.is_json or request.headers.get(
                'X-Requested-With') == 'XMLHttpRequest'
            if wants_json:
                return jsonify(
                    {'error': 'forbidden', 'reason': 'organizer_required'}), 403
            return redirect(url_for('dashboard'))

        return wrapped

    def abstract_grader_required(view):
        ''' Decorator to require abstract grader or organizer role for a view. '''
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_info = session.get('user')
            if not user_info:
                return redirect(url_for('google_login'))

            email = user_info.get('email')
            if not email:
                return redirect(url_for('google_login'))

            db_user = user.query.filter_by(email=email).first()
            if not db_user:
                return redirect(url_for('signup'))

            roles = []
            if db_user.auth:
                roles = [r.strip().lower()
                         for r in str(db_user.auth).split(',') if r.strip()]

            if 'organizer' in roles or 'abstract-grader' in roles:
                return view(*args, **kwargs)

            wants_json = request.is_json or request.headers.get(
                'X-Requested-With') == 'XMLHttpRequest'
            if wants_json:
                return jsonify(
                    {'error': 'forbidden', 'reason': 'abstract_grader_required'}), 403
            return redirect(url_for('dashboard'))

        return wrapped

    def banned_user_redirect(view):
        ''' Decorator to redirect banned users to a specific page. '''
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_info = session.get('user')
            if not user_info:
                return view(*args, **kwargs)

            email = user_info.get('email')
            if not email:
                return view(*args, **kwargs)

            db_user = user.query.filter_by(email=email).first()
            if not db_user:
                return view(*args, **kwargs)

            roles = []
            if db_user.auth:
                roles = [r.strip().lower()
                         for r in str(db_user.auth).split(',') if r.strip()]

            if 'banned' in roles:
                return redirect(url_for('fizzbuzz'))

            return view(*args, **kwargs)

        return wrapped

    def presenter_required(view):
        ''' Decorator to require presenter or organizer role for a view. '''
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_info = session.get('user')
            if not user_info:
                return redirect(url_for('google_login'))

            email = user_info.get('email')
            if not email:
                return redirect(url_for('google_login'))

            db_user = user.query.filter_by(email=email).first()
            if not db_user:
                return redirect(url_for('signup'))

            if db_user.auth in ('presenter', 'organizer'):
                return view(*args, **kwargs)

            wants_json = request.is_json or request.headers.get(
                'X-Requested-With') == 'XMLHttpRequest'
            if wants_json:
                return jsonify(
                    {'error': 'forbidden', 'reason': 'presenter_required'}), 403
            return redirect(url_for('dashboard'))

        return wrapped

    @app.context_processor
    def inject_permissions():
        ''' Inject user permissions and roles into templates.'''
        user_info = session.get('user')
        email = user_info.get('email') if user_info else None

        db_user = None
        roles = []

        if email:
            db_user = user.query.filter_by(email=email).first()
            if db_user and db_user.auth:
                roles = [r.strip().lower()
                         for r in str(db_user.auth).split(',') if r.strip()]

        is_authenticated = bool(user_info)
        is_organizer = 'organizer' in roles
        is_presenter = 'presenter' in roles

        allowed_programs = set()
        if is_presenter or is_organizer:
            allowed_programs.update(['poster', 'presentation', 'blitz'])

        user_name = None
        user_picture = None
        if user_info:
            user_name = user_info.get('name') or user_info.get('email')
            user_picture = user_info.get('picture')

        return{
            "db_user": db_user,
            "roles": roles,
            "is_organizer": is_organizer,
            "is_presenter": is_presenter,
            "allowed_programs": allowed_programs,
            "is_authenticated": is_authenticated,
            "user_name": user_name,
            "user_picture": user_picture,
        }

    return (organizer_required,
            abstract_grader_required,
            banned_user_redirect,
            presenter_required)
