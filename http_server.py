import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

import time
import csv
import io
import matplotlib.pyplot as plt
from flask import send_file



app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Path to the JSON file where user data will be stored
users_file = 'users.json'


# Load user data from the JSON file
def load_users():
    try:
        with open(users_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Save user data to the JSON file
def save_users(users):
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)


@app.route('/')
def home():
    # Check if the user is logged in
    if 'username' in session:
        return f'Hello, {session["username"]}! <a href="/logout">Logout</a>'
    return "Welcome to the Home Page! <a href='/login'>Go to login page</a>"


@app.route('/login', methods=['GET', 'POST'])
def login():
    users_db = load_users()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists and the password matches
        if username in users_db and check_password_hash(users_db[username]['password'], password):
            session['username'] = username  # Store username in session
            flash('Login successfully!', 'success')
            return redirect(url_for('redirect_page'))  # Redirect to the intermediate page
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/redirect_page')
def redirect_page():
    if 'username' in session:
        return render_template('redirect_page.html')
    else:
        return redirect(url_for('login'))

@app.route('/settings')
def settings():
    if 'username' in session:
        return render_template('settings.html')
    else:
        return redirect(url_for('login'))



# Function to fetch data from a CSV file
def fetch_data():
    data = []
    with open('data.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data


# Route to render the main page
@app.route('/main')
def main():
    if 'username' in session:
        return render_template('main.html')
    else:
        return redirect(url_for('login'))


# Route to generate and return the plot image
@app.route('/plot_data')
def plot_data():
    data = fetch_data()  # Fetch the data from the CSV
    dates = [row['date'] for row in data]
    values = [float(row['value']) for row in data]

    # Create a plot with Matplotlib
    plt.figure(figsize=(10, 5))
    plt.plot(dates, values, marker='o')
    plt.title('Data Plot')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.xticks(rotation=45)

    # Save plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # Return the image as a response
    return send_file(img, mimetype='image/png')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    users_db = load_users()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        telephone = request.form['telephone']

        # Hash the password with the correct method
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Check if the user already exists
        if username in users_db:
            flash('Username already exists! Please choose a different one.')
            return redirect(url_for('signup'))

        # Add new user to the database with the telephone number
        users_db[username] = {
            'password': hashed_password,
            'telephone': telephone
        }
        save_users(users_db)  # Save the updated users to the JSON file
        flash('User registered successfully! You can now log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')



# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove user from session
    flash('You have been logged out.')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
