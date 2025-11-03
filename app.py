from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def program():
    return render_template('organizer.html')

@app.route('/organizer')
def organizer():
    return render_template('organizer.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/abstractGrader')
def abstractGrader():
    return render_template('abstractGrader.html')

@app.route('/schedule')
def schedule():
    return render_template('organizer.html')

@app.route('/attendees')
def attendees():
    return render_template('organizer.html')

if __name__ == '__main__':
    app.run(debug=True)
