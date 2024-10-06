import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session

import time
import csv
import io
import matplotlib.pyplot as plt
from flask import send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Replace this with the IP address of your Raspberry Pi running the Flask database server
raspi_url = "http://192.168.133.95:5000"



def save_user(data):
    try:
        response = requests.post(f"{raspi_url}/register", json=data)
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def authenticate_user(data):
    try:
        response = requests.post(f"{raspi_url}/login", json=data)
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def add_chat_id(data):
    try:
        response = requests.post(f"{raspi_url}/add_chat_id", json=data)
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


@app.route('/')
def home():
    # Check if the user is logged in
    if 'username' in session:
        return f'Hello, {session["username"]}! <a href="/logout">Logout</a>'
    return "Welcome to the Home Page! <a href='/login'>Go to login page</a>"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Prepare data for the Raspberry Pi Flask database server
        data = {
            "username": username,
            "password": password
        }

        # Check if the username exists and the password matches by sending a request to the database server
        response = authenticate_user(data)

        if response and response.status_code == 200:
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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        telephone = request.form['telephone']
        auth_method = request.form['auth_method']  # Fetch the chosen authentication method


        # Prepare user data for registration
        user_data = {
            'username': username,
            'password': password,
            'telephone': telephone,
            'auth_method': auth_method,
            'chat_id': None  # Initially no chat ID
        }

        # Send a request to the Raspberry Pi server to save the user
        response = save_user(user_data)

        if response and response.status_code == 201:
            flash('Signup successful!', 'success')
            if auth_method == 'telegram':
                return redirect(url_for('telegram_instructions'))
            elif auth_method == 'whatsapp':
                return redirect(url_for('whatsapp_auth'))
        else:
            flash('Signup failed. Please try again.', 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')


# Route for Telegram authentication instructions
@app.route('/telegram_instructions')
def telegram_instructions():
    return render_template('telegram_instructions.html')


# Route for WhatsApp authentication instructions
@app.route('/whatsapp_auth')
def whatsapp_auth():
    return "You have chosen WhatsApp authentication. (Implement WhatsApp API here)"


# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove user from session
    flash('You have been logged out.')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
