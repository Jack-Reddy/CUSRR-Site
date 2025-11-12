from flask import Flask, render_template
from flask import session, redirect, url_for, jsonify, request
import os
import auth
import requests
from dotenv import load_dotenv
from models import db
from routes.users import users_bp
from routes.presentations import presentations_bp
from routes.abstract_grades import abstract_grades_bp
from routes.grades import grades_bp
from seed import seed_data
from config import Config
from models import User
from functools import wraps

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET')

auth.init_oauth(app)
google = auth.oauth.create_client('google')


def organizer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_info = session.get('user')
        if not user_info:
            return redirect(url_for('google_login'))

        email = user_info.get('email')
        if not email:
            return redirect(url_for('google_login'))

        db_user = User.query.filter_by(email=email).first()
        if not db_user:
            return redirect(url_for('signup'))

        if db_user.auth == 'organizer':
            return view(*args, **kwargs)

        # not permitted: return 403 for API/XHR, or redirect to dashboard
        wants_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if wants_json:
            return jsonify({'error': 'forbidden', 'reason': 'organizer_required'}), 403
        # redirect to dashboard
        return redirect(url_for('dashboard'))
    return wrapped


def abstract_grader_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_info = session.get('user')
        if not user_info:
            return redirect(url_for('google_login'))

        email = user_info.get('email')
        if not email:
            return redirect(url_for('google_login'))

        db_user = User.query.filter_by(email=email).first()
        if not db_user:
            return redirect(url_for('signup'))

        roles = []
        if db_user.auth:
            roles = [r.strip().lower() for r in str(db_user.auth).split(',') if r.strip()]

        if 'organizer' in roles or 'abstract_grader' in roles:
            return view(*args, **kwargs)

        # not permitted: return 403 for API/XHR, or redirect to dashboard
        wants_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if wants_json:
            return jsonify({'error': 'forbidden', 'reason': 'abstract_grader_required'}), 403
        return redirect(url_for('dashboard'))

    return wrapped

def presenter_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_info = session.get('user')
        if not user_info:
            return redirect(url_for('google_login'))

        email = user_info.get('email')
        if not email:
            return redirect(url_for('google_login'))

        db_user = User.query.filter_by(email=email).first()
        if not db_user:
            return redirect(url_for('signup'))

        if db_user.auth == 'presenter':
            return view(*args, **kwargs)

        # not permitted: return 403 for API/XHR, or redirect to dashboard
        wants_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if wants_json:
            return jsonify({'error': 'forbidden', 'reason': 'presenter_required'}), 403
        # redirect to dashboard
        return redirect(url_for('dashboard'))
    return wrapped



app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(users_bp, url_prefix="/api/v1/users")
app.register_blueprint(presentations_bp, url_prefix="/api/v1/presentations")
app.register_blueprint(abstract_grades_bp, url_prefix='api/v1/abstractgrades')
app.register_blueprint(grades_bp, url_prefix='/grades')

@app.route('/')
def program():
    return render_template('dashboard.html')

@app.route('/organizer')
def organizer():
    return render_template('organizer.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/abstractGrader')
@abstract_grader_required
def abstractGrader():
    return render_template('abstractGrader.html')

@app.route('/schedule')
def schedule():
    return render_template('organizer.html')

@app.route('/organizer-user-status')
@organizer_required
def organizer_user_status():
    return render_template('organizer-user-status.html')

@app.route('/attendees')
def attendees():
    return render_template('organizer.html')


#Authentication Routes
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
            headers={'Accept': 'application/json'}
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
                            'values': ['accounts.google.com', 'https://accounts.google.com']
                        }
                    }
                )
            except Exception:
                # If ID token validation fails, fetch userinfo via OIDC endpoint
                if access_token:
                    resp = requests.get(
                        'https://openidconnect.googleapis.com/v1/userinfo',
                        headers={'Authorization': f'Bearer {access_token}'}
                    )
                    user_info = resp.json()
                else:
                    user_info = {'error': 'no_access_token_after_id_token_failure', 'detail': token_json}
        else:
            if access_token:
                resp = requests.get(
                    'https://openidconnect.googleapis.com/v1/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                user_info = resp.json()
            else:
                user_info = {'error': 'no id_token or access_token', 'detail': token_json}
    except Exception as e:
        user_info = {'error': 'token_exchange_failed', 'detail': str(e), 'token_resp': locals().get('token_json')}

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
    db_user = User.query.filter_by(email=email).first()  # check if account exists
    print(bool(db_user))

    return jsonify({
        'authenticated': True,
        'name': user.get('name'),
        'email': email,
        'picture': user.get('picture'),
        'account_exists': bool(db_user),  # True if user exists in DB
        'user_id': db_user.id if db_user else None,  # optionally include the DB id
        'auth': db_user.auth if db_user else None
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
@presenter_required
def profile():
    return render_template('profile.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from models import User
        if User.query.count() == 0:
            seed_data()
    app.run(debug=True)
