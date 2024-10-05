# app.py
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for session management and flash messages

# Dummy user data for login validation
users = {
    'admin': 'password123',
    'user': 'mysecretpassword'
}

@app.route('/')
def home():
    return "Welcome to the Home Page! <a href='/login'>Go to login page</a>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate the username and password
        if username in users and users[username] == password:
            return f'Welcome, {username}!'
        else:
            flash('Invalid username or password. Please try again.')
            return redirect(url_for('login'))
    
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
