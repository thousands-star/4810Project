import configparser

class ConfigReader:
    """
    A class to read and store configuration from a config.txt file,
    and provide functions to query parameters for other classes.
    """
    
    def __init__(self, config_file='config.txt'):
        self.config_file = config_file
        self.config_data = {}
        self._read_config()

    def _read_config(self):
        """
        Reads the configuration file and stores the values in a dictionary.
        """
        config = configparser.ConfigParser()
        config.read(self.config_file)

        # Store all config sections and key-value pairs in a dictionary
        for section in config.sections():
            self.config_data[section] = {}
            for key, value in config.items(section):
                self.config_data[section][key] = value

    def get_param(self, section, key):
        """
        Retrieves the value of a given parameter from the specified section.
        
        :param section: The section from which to retrieve the key
        :param key: The key whose value is to be retrieved
        :return: The value associated with the key, or None if not found
        """
        return self.config_data.get(section, {}).get(key)

    def get_all_params(self):
        """
        Returns the entire configuration as a dictionary.
        
        :return: The configuration dictionary
        """
        return self.config_data

    def print_params(self):
        """
        Prints out all configuration parameters in a formatted way.
        """
        for section, params in self.config_data.items():
            print(f"[{section}]")
            for key, value in params.items():
                print(f"{key} = {value}")
            print()  # Blank line between sections
