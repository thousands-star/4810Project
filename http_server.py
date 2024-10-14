import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
import random
import time
import csv
import io
import matplotlib.pyplot as plt
from flask import send_file, send_from_directory
from server import TelegramBot
from config_reader import ConfigReader
import os
import rsa
import base64
from model_socket import initialize_model, predict_roc, predict_useuptime, read_fullness


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Replace this with the IP address of your Raspberry Pi running the Flask database server
configReader = ConfigReader()
telegram_token = configReader.get_param('TELEGRAM', 'token')
ip = configReader.get_param('RASPI', 'ip')
port_num = configReader.get_param('RASPI', 'port_num')
raspi_url = f"http://{ip}:{port_num}"
print(raspi_url)
public_key = None
model_list = initialize_model()

def get_public_key():
    global public_key
    # Request the public key from the server
    print("\n-----------Get Public Key Session----------")
    response = requests.get(f"{raspi_url}/get_public_key")
    public_key_pem = response.json()['public_key']
    print("Public key retrieved!")
    print("Public Key:")
    
    # Load the public key
    public_key = rsa.PublicKey.load_pkcs1(public_key_pem.encode())
    print(public_key)
    print("-------------------------------------------\n")


def encrypt_json(data):
    global public_key
    print("+++++++++++++++Encryption Session+++++++++++++++")
    print("Original Data:")
    print(data)
    get_public_key()

    # Encode the JSON credentials in base64
    json_credentials = json.dumps(data)
    encoded_credentials = json_credentials.encode()
    # Encrypt the credentials using the public key
    encrypted_message = rsa.encrypt(encoded_credentials, public_key)
    # Encode the encrypted message in base64 for HTTP transmission
    encrypted_message_base64 = base64.b64encode(encrypted_message).decode()
    print("\n Encrypted Message:")
    print(encrypted_message_base64 + "\n")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++")
    return encrypted_message_base64


def save_user(data):
    try:
        response = requests.post(f"{raspi_url}/register", json={"encrypted_message": encrypt_json(data)})
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        get_public_key()
        return None

def authenticate_user(data):
    try:
        response = requests.post(f"{raspi_url}/login", json={"encrypted_message": encrypt_json(data)})
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        get_public_key()
        return None

def add_chat_id(data):
    try:
        response = requests.post(f"{raspi_url}/add_chat_id", json={"encrypted_message": encrypt_json(data)})
        return response
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        get_public_key()
        return None

def get_chat_id(username, password):
    try:
        # Send both username and password to the database server for verification
        data = {"username": username, "password": password}
        response = requests.post(f"{raspi_url}/get_chat_id", json={"encrypted_message": encrypt_json(data)})

        if response.status_code == 200:
            chat_id = response.json().get('chat_id')
            print("Get chat_id successfully")
            return chat_id
        else:
            print(f"Error: {response.json().get('error')}")
            return None
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        get_public_key()
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

        # Authenticate the user (check username and password)
        response = authenticate_user(data)

        if response and response.status_code == 200:
            # Try to get the chat_id from the Raspberry Pi database
            chat_id = get_chat_id(username, password)

            print(f"Chat ID retrieved: {chat_id}")
            
            if chat_id:
                # Generate OTP and send via Telegram
                otp = generate_otp()
                session['otp'] = otp  # Store OTP in the session for verification

                if send_otp_telegram(chat_id, otp):
                    flash('OTP sent to your Telegram!', 'success')
                    session['username'] = username  # Store username in session for further use
                    return redirect(url_for('verify_otp_page'))
                else:
                    flash('Failed to send OTP. Please try again.', 'error')
                    return redirect(url_for('login'))
            else:
                flash('No Telegram chat ID found for user.', 'error')
                return redirect(url_for('login'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp_page():
    if request.method == 'POST':
        input_otp = request.form['otp']

        # Verify the OTP entered by the user
        if verify_otp(input_otp):
            session.pop('otp', None)  # OTP is valid, remove it from session
            flash('Login successful!', 'success')
            return redirect(url_for('redirect_page'))  # Redirect to home page
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return redirect(url_for('verify_otp_page'))

    return render_template('verify_otp.html')



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
        fullness_list = read_fullness()
        roc_list = []
        depletion_list = []
        for i in range(len(fullness_list)):
            roc_list.append(round(predict_roc(model_list[i]), 2))
            depletion_list.append(predict_useuptime(fullness_list[i], model_list[i]))
            
        # Placeholder data for ROC and depletion times for each tank
        # roc_sugar = 5  # Example: Rate of consumption in kg/day
        # depletion_sugar = "2024-11-30"  # Example: Expected depletion date
        # roc_grains = 3  # Example for Tank 2
        # depletion_grains = "2024-12-15"
        # roc_flour = 4  # Example for Tank 3
        # depletion_flour = "2024-12-20"
        # roc_legumes = 2  # Example for Tank 4
        # depletion_legumes = "2025-01-05"
        return render_template('main.html', 
                               roc_grains=roc_list[0], depletion_grains=depletion_list[0],
                               roc_sugar=roc_list[1], depletion_sugar=depletion_list[1],
                               roc_flour=roc_list[2], depletion_flour=depletion_list[2], 
                               roc_legumes=roc_list[3], depletion_legumes=depletion_list[3])
    else:
        return redirect(url_for('login'))



# Route to generate and return the plot image
@app.route('/plot_data')
def plot_data():
    # Path to the directory where 'dustbin_fullness.png' is located
    image_directory = app.root_path  # Assuming the image is in the 'static' folder
    image_filename = 'storagetank_fullness.png'
    # Return the image from the static folder
    return send_from_directory(image_directory, image_filename, mimetype='image/png')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        telephone = request.form['telephone']
        selfie = request.files.get('selfie')  # Get the uploaded image if provided

        # Prepare user data for registration
        user_data = {
            'username': username,
            'password': password,
            'telephone': telephone,
            'auth_method': 'telegram',  # Default authentication method is Telegram
            'chat_id': None  # Initially no chat ID
        }

        # Handle image upload (optional)
        if selfie:
            selfie.save(f'static/uploads/{username}.jpg')  # Save the image as username.jpg

        # Send a request to the Raspberry Pi server to save the user
        response = save_user(user_data)

        if response and response.status_code == 201:
            flash('Signup successful!', 'success')
            # Redirect to Telegram instructions by default
            return redirect(url_for('telegram_instructions'))
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

# Function to generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Function to send OTP via Telegram
def send_otp_telegram(chat_id, otp):
    bot_token = telegram_token  # Replace with your Telegram bot token
    message = f"Your OTP is: {otp}"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message
        }
        response = requests.post(url, data=data)
        
        # Log the response details
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to send OTP: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False


# Function to verify OTP (you can store the generated OTP in the session)
def verify_otp(input_otp):
    return input_otp == session.get('otp')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
