from flask import Flask, render_template
from models import db
from routes.users import users_bp
from routes.presentations import presentations_bp
from seed import seed_data
from config import Config

app = Flask(__name__)

app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(users_bp, url_prefix="/api/users")
app.register_blueprint(presentations_bp, url_prefix="/api/presentations")

@app.route('/')
def program():
    return render_template('organizer.html')

@app.route('/organizer')
def organizer():
    return render_template('organizer.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/schedule')
def schedule():
    return render_template('organizer.html')

@app.route('/attendees')
def attendees():
    return render_template('organizer.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from models import User
        if User.query.count() == 0:
            seed_data()
    app.run(debug=True)
