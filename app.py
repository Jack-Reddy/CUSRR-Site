from flask import Flask, render_template
from flask import session, redirect, url_for, jsonify, request
import os
import auth
import requests
from authlib.jose.errors import InvalidClaimError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET')

auth.init_oauth(app)
google = auth.oauth.create_client('google')

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('google_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def program():
    return render_template('organizer.html')

@app.route('/organizer')
def organizer():
    return render_template('organizer.html')

@app.route('/schedule')
def schedule():
    return render_template('organizer.html')

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

    # Manually exchange the authorization code for tokens. We do this rather
    # than calling Authlib's authorize_access_token() to avoid consuming the
    # code in a way that prevents our fallback logic from working.
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
    return redirect(url_for('program'))

@app.route('/google/logout')
def google_logout():
    session.pop('user', None)
    return redirect('/')


@app.route('/me')
def me():
    user = session.get('user')
    if not user:
        return jsonify({'authenticated': False}), 401
    return jsonify({
        'authenticated': True,
        'name': user.get('name'),
        'email': user.get('email'),
        'picture': user.get('picture')
    })


if __name__ == '__main__':
    app.run(debug=True)
