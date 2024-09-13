class UserAuthenticator:
    _user_credentials = {}  # Class variable to hold user credentials
    
    @classmethod
    def load_users(cls, file_path='security/users.txt'):
        """
        Load user credentials from the text file and store them in the class variable.
        """
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    username, password = line.strip().split(':')
                    cls._user_credentials[username] = password
            # print("User data loaded successfully.")
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")
    
    @classmethod
    def check(cls, username, password):
        """
        Validate the username and password against the stored credentials.
        """
        
        cls.load_users()

        stored_password = cls._user_credentials.get(username)
        if stored_password is not None and stored_password == password:
            return True
        return False
    
    @classmethod
    def add_user(cls, username, password, file_path='security/users.txt'):
        """
        Add a new user to the credentials file and update the class variable.
        """
        # Ensure users are loaded
        cls.load_users(file_path)
        
        # Check if the username already exists
        if username in cls._user_credentials:
            return False, "Username already taken."

        # Add the new user to the class variable
        cls._user_credentials[username] = password

        # Append the new user to the file
        try:
            with open(file_path, 'a') as file:
                file.write(f"{username}:{password}\n")
            return True, "User added successfully."
        except Exception as e:
            return False, f"Error occurred while adding user: {str(e)}"