from flask import Flask, render_template
from flask import session, redirect, url_for
import auth

app = Flask(__name__)

auth.init_oauth(app)
google = auth.oauth.create_client('google')

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
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['user'] = user_info
    return redirect(url_for('program'))

@app.route('/google/logout')
def google_logout():
    session.pop('user', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
