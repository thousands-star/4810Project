import requests
import asyncio
from aiogram import Bot
from telethon import TelegramClient, events, Button
from aiogram.types import FSInputFile # use for message handler
from config_reader import ConfigReader
import time
# this is for encryption
import rsa
import json
import base64
from model_socket import initialize_model, predict_roc, predict_useuptime, read_fullness, convert_minutes

class TelegramBot:
    """
    A Telegram bot that interacts with users and performs various tasks related to dustbin monitoring and analysis.
    """
    def __init__(self, configReader: ConfigReader, exist_analyser=True):
        # Parameter
        self.exist_analyser = exist_analyser
        token = configReader.get_param('TELEGRAM', 'token')
        api_id = configReader.get_param('TELEGRAM', 'api_id')
        api_hash = configReader.get_param('TELEGRAM', 'api_hash')
        self.interval = int(configReader.get_param('TELEGRAM', 'interval'))
        self.alert_frequency = int(configReader.get_param('TELEGRAM', 'alert_frequency'))
        self.fullness_alert_threshold = float(configReader.get_param('TELEGRAM', 'fullness_alert_threshold'))
        self.depletion_alert_threshold = float(configReader.get_param('TELEGRAM', 'depletion_alert_threshold'))
        
        self.count = 0
        self.chat_ids = set()  # Store chat_ids of users who interact with the bot
        self.logged_in_users = set()
        self.pending_login = {}  # Track login state for each user
        ip = configReader.get_param('RASPI', 'ip')
        port_num = configReader.get_param('RASPI', 'port_num')
        self.flask_server_url = f"http://{ip}:{port_num}"
        print(self.flask_server_url)
        self.public_key = None
        # Set up telegram bot and dustbin analyzer
        print(token)
        self.bot = Bot(token)
        self.client = TelegramClient('bot', api_id, api_hash).start(bot_token=token)
        self.model_list = initialize_model()
        # Register event handlers
        self.register_handlers()
    

    def get_public_key(self):
        # Request the public key from the server
        print("\n-----------Get Public Key Session----------")
        response = requests.get(f"{self.flask_server_url}/get_public_key")
        public_key_pem = response.json().get('public_key')
        print("Public key retrieved!")
        print("Public Key:")
        
        # Load the public key
        self.public_key = rsa.PublicKey.load_pkcs1(public_key_pem.encode())
        print(self.public_key)
        print("-------------------------------------------\n")


    def encrypt_json(self,data):
        print("+++++++++++++++Encryption Session+++++++++++++++")
        print("Original Data:")
        print(data)
        if self.public_key is None:
            self.get_public_key()
        else:
            print("\nPublic Key:")
            print(self.public_key)
        
        json_credentials = json.dumps(data)
        encoded_credentials = json_credentials.encode()
        # Encrypt the credentials using the public key
        encrypted_message = rsa.encrypt(encoded_credentials, self.public_key)
        # Encode the encrypted message in base64 for HTTP transmission
        encrypted_message_base64 = base64.b64encode(encrypted_message).decode()
        print("\n Encrypted Message:")
        print(encrypted_message_base64 + "\n")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++")
        return encrypted_message_base64
    
    def authenticate_user(self, username, password):
        """
        Sends login credentials to the Flask server for authentication.
        """
        data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(f"{self.flask_server_url}/login", json={"encrypted_message": self.encrypt_json(data)})
            return response
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None

    def add_chat_id(self, username, chat_id):
        """
        Sends the user's chat_id to the Flask server after successful login.
        """
        data = {
            "username": username,
            "chat_id": chat_id
        }
        try:
            response = requests.post(f"{self.flask_server_url}/add_chat_id", json={"encrypted_message": self.encrypt_json(data)}) # encrypt_json(data)
            if response.status_code == 200:
                print(f"Chat ID for {username} successfully added to the database.")
            else:
                print(f"Failed to add chat ID for {username}.")
        except Exception as e:
            print(f"Error adding chat ID: {e}")


    """
    Handlers
    """
    def register_handlers(self):
        # Registering the event handlers
        self.client.on(events.NewMessage(pattern='Send me to real-time'))(self.realTimeGraph)
        self.client.on(events.NewMessage(pattern='/start'))(self.main_menu)
        self.client.on(events.NewMessage(pattern='Back!'))(self.main_menu)
        self.client.on(events.NewMessage(pattern='who_is_in'))(self.who_is_in_handler)
        self.client.on(events.NewMessage(pattern='Monitor who is in the factory'))(self.who_is_in_handler)
        self.client.on(events.NewMessage(pattern='Send me a data analysis'))(self.sendDataAnalysis)
        self.client.on(events.NewMessage(pattern='Send me a graph of current fullness!'))(self.sendGraph)
        self.client.on(events.NewMessage(pattern='Login'))(self.login_handler)
        self.client.on(events.NewMessage(incoming=True))(self.handle_message)  # Catch all other messages
        self.client.on(events.NewMessage(pattern='/help'))(self.help_handler)
        self.client.on(events.NewMessage(pattern='/logout'))(self.logout_handler)
        self.client.on(events.NewMessage(pattern='/quit'))(self.quit_handler)

    async def quit_handler(self, event):
        """
        Gracefully shut down the bot on the /quit command.
        """
        user_id = event.sender_id
        await event.respond("The bot is shutting down. Goodbye!")

        # Stop the bot and disconnect the client
        await self.client.disconnect()  # Disconnect the Telegram client

        # Stop the event loop after the bot responds
        loop = asyncio.get_event_loop()
        loop.stop()

    async def logout_handler(self, event):
        """
        Log out the user by removing them from the logged_in_users set.
        """
        user_id = event.sender_id
        if user_id in self.logged_in_users:
            self.logged_in_users.remove(user_id)
            await event.respond("You have been logged out. Please log in again using /start.")
        else:
            await event.respond("You are not logged in.")

    async def help_handler(self, event):
        """
        Provide a list of available commands and their descriptions.
        """
        help_text = (
            "Here are the available commands:\n"
            "/start - Start the bot and see the main menu\n"
            "/help - Show this help message\n"
            "/logout - Log out of the bot\n"
            "/who_is_in - Show who is in the factory\n"
            "\n"
            "Other commands available through buttons:\n"
            "- Real-time data\n"
            "- Data analysis\n"
            "- Graph of current fullness\n"
        )
        await event.respond(help_text)

    async def login_handler(self, event):
        user_id = event.sender_id
        self.pending_login[user_id] = {'step': 1, 'action': 'login'}
        time.sleep(1)
        await event.respond("Please enter your username:")

    async def handle_message(self, event):
        user_id = event.sender_id
        text = event.message.text.strip()
        print(text)

        # Check if the user is in the middle of the login process
        if user_id in self.pending_login:
            state = self.pending_login[user_id]
            step = state['step']

            # Step 1: Get Username
            if step == 1:
                if text == 'Login' or text == 'Sign Up':
                    return
                state['username'] = text  # Store the entered username
                state['step'] = 2  # Move to the next step (asking for password)
                await event.respond("Please enter your password:")

            # Step 2: Get Password and handle login
            elif step == 2:
                password = text
                username = state['username']

                if state['action'] == 'login':
                    # Send a request to the Raspberry Pi Flask server to check the login credentials
                    response = self.authenticate_user(username, password)
                    if response and response.status_code == 200:
                        self.logged_in_users.add(user_id)

                        # Register the user's chat_id on the server
                        self.add_chat_id(username, user_id)
                        self.chat_ids.add(user_id)
                        del self.pending_login[user_id]  # Clear pending login
                        await event.respond(f"Welcome, {username}! You are now logged in.")
                        await self.main_menu(event)
                    else:
                        await event.respond("Invalid username or password. Please try again.")
                        del self.pending_login[user_id]  # Clear pending login after failed attempt

        else:
            await event.respond("Use /help to get more info.")

    # This function responsible for sending the analyzed data to the telegram bot 
    async def sendDataAnalysis(self, event):
        if event.sender_id not in self.logged_in_users:
            await self.main_menu(event)
            return
        with open('analysis.txt', 'r') as file:
            # Read the entire file content into a string
            message = file.read()
            await self.bot.send_message(event.chat_id, message)

    # This function responsible for sending the analyzed graph to the telegram bot 
    async def sendGraph(self, event):
        if event.sender_id not in self.logged_in_users:
            await self.main_menu(event)
            return
        await self.bot.send_message(event.chat_id, "Here is the graph of the current fullness:")
        file_to_send = FSInputFile("storagetank_fullness.png")
        await self.bot.send_document(event.chat_id, file_to_send)

    # This function responsible for sending a web-based real-time analyzed data 
    async def realTimeGraph(self, event):
        if event.sender_id not in self.logged_in_users:
            await self.main_menu(event)
            return
        await event.respond(
            'Link to real-time graphing:',
            buttons=[
                [Button.url('ThingSpeak', 'https://thingspeak.com/channels/2622766')],
            ]
        )

    # This function responsible for creating button to display a menu list in the telegram bot 
    async def main_menu(self, event):
        user_id = event.sender_id
        if user_id not in self.logged_in_users:
            await event.respond(
                "Welcome to the bot! Please select an option:",
                buttons=[
                    [Button.text('Login')]
                ]
            )
            return

        await event.respond(
            'Welcome to the bot! Choose an option:',
            buttons=[
                [Button.text('Send me to real-time')],
                [Button.text('Send me a data analysis')],
                [Button.text('Send me a graph of current fullness!')],
                [Button.text('Monitor who is in the factory')]
            ]
        )

    """
        To monitor who is inside the factory in real time
    """
    async def who_is_in_handler(self, event):
        """
        Handler that retrieves the list of current occupants from the Flask server
        and sends that information to the Telegram chat.
        """
        user_id = event.sender_id
        print(f"Received '/who_is_in' command from user {user_id}")  # Debugging print

        if user_id not in self.logged_in_users:
            await event.respond("You need to log in to use this feature.")
            return

        # Make a request to the Flask server to get the list of occupants
        try:
            response = requests.get(f"{self.flask_server_url}/who_is_in")
            if response.status_code == 200:
                occupants_data = response.json()
                occupants_list = occupants_data.get("occupants", [])

                if occupants_list:
                    occupants_str = "\n".join(occupants_list)
                    await event.respond(f"Current occupants in the factory:\n{occupants_str}")
                else:
                    await event.respond("There is no one currently inside the factory.")
            else:
                await event.respond("Failed to retrieve occupants. Please try again later.")
        except Exception as e:
            print(f"Error requesting occupants list: {e}")
            await event.respond("An error occurred while fetching the list of occupants.")

    """
    Dustbin Analyser(To get the lastest data and plot)
    """
    async def periodic_task(self):
        while True:
            self.count += 1
            if not self.exist_analyser:
                # print("No data analyser available.")
                print("pending", self.pending_login)
                print("logged in", self.logged_in_users)
            else:
                # load the analysis.txt and storagetank_fullness.png
                # Download analysis.txt
                analysis_response = requests.get(f"{self.flask_server_url}/get_analysis")
                if analysis_response.status_code == 200:
                    with open('analysis.txt', 'wb') as file:
                        file.write(analysis_response.content)
                    print("analysis.txt downloaded successfully.")
                else:
                    print("Failed to download analysis.txt")

                # Download storagetank_fullness.png
                image_response = requests.get(f"{self.flask_server_url}/get_fullness_image")
                if image_response.status_code == 200:
                    with open('storagetank_fullness.png', 'wb') as file:
                        file.write(image_response.content)
                    print("storagetank_fullness.png downloaded successfully.")
                else:
                    print("Failed to download storagetank_fullness.png")
                
                # Get fullness.txt from Flask API
                response_txt = requests.get(f"{self.flask_server_url}/get_fullness_txt")
                if response_txt.status_code == 200:
                    with open('fullness.txt', 'wb') as f:
                        f.write(response_txt.content)  # Save the fullness.txt locally
                    print("fullness.txt downloaded successfully.")
                    message_list = self.handle_alert_message()
                    print("Message list:", message_list)
                    print("CHAT IDS:", self.chat_ids)
                    if message_list:
                        for message in message_list:
                            for chat_id in self.chat_ids:
                                await self.bot.send_message(chat_id, message)
                else:
                    print("Failed to fullness.txt")
                    
                                
            await asyncio.sleep(self.interval)
                        
    
    def handle_alert_message(self):
        # Open the file for reading
        message_list = []
        fullness_list, name_list = read_fullness()
        # message_list.append("Alert ! ! !")
        # with open('fullness.txt', 'r') as file:
        #     for line in file:
        #         line = line.strip()
        #         name, fullness = line.split()
        #         # Convert fullness to a float
        #         fullness = float(fullness)
        #         # Print the results (or do something with them)
        #         # print(f"Item: {name}, Fullness: {fullness}")
        for i in range(len(fullness_list)):
            # if (fullness_list[i] < self.fullness_alert_threshold):
            #     if i == 0:
            #         message_list.append("Alert ! ! !")
            #     message = f"The stock of {name_list[i]} is running low at {fullness_list[i]:.2f}%. Please consider restocking soon."
            #     message_list.append(message)
            #     depletion_time = predict_useuptime(fullness_list[i], self.model_list[i], False)
            #     if depletion_time < self.depletion_alert_threshold:
            #         day, hour, minute = convert_minutes(depletion_time)
            #         message = f"{name_list[i]} will be depleted in {day} days {hour} hours {minute} minutes. Please restock soon."
            #         message_list.append(message)
            current_fullness = fullness_list[i]
            depletion_time = predict_useuptime(current_fullness, self.model_list[i], False)
            if depletion_time < self.depletion_alert_threshold:
                if i == 0:
                    message_list.append("Alert ! ! !")
                day, hour, minute = convert_minutes(depletion_time)
                message = f"{name_list[i]} will be depleted in {day} days {hour} hours {minute} minutes. Please restock soon."
                message_list.append(message)
            
        # print(message_list)
        return message_list
                    
    """
    Bot operations 
    """
    # This function is responsible to start listening from the telegram client 
    async def run(self):
        # Start the client in the main thread
        await self.client.start()
        await self.client.run_until_disconnected()