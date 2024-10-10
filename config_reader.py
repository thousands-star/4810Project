import configparser

class ConfigReader:
    def __init__(self, config_file='config.txt'):
        self.config_file = config_file
        self.config_data = {}
        self._read_config()

    def _read_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)

        for section in config.sections():
            self.config_data[section] = {}
            for key, value in config.items(section):
                self.config_data[section][key] = value

    def get_param(self, section, key):
        return self.config_data.get(section, {}).get(key)

    def get_list(self, section, key, delimiter=","):
        value = self.get_param(section, key)
        if value:
            return value.split(delimiter)
        return []

    def get_storagetank_info(self):
        """
        Returns a list of dustbin information from the config.
        """
        storage_tanks = []
        for section in self.config_data:
            if section.startswith("STORAGE_TANK_"):
                depth = float(self.get_param(section, "depth"))
                tag = self.get_param(section, "tag")
                storage_tanks.append({"depth": depth, "tag": tag})
        return storage_tanks

    def get_thingspeak_info(self):
        """
        Returns the ThingSpeak read/write API keys and channel IDs.
        """
        read_api_keys = self.get_list('THINGSPEAK', 'read_api_keys')
        us_write_api_keys = self.get_list('THINGSPEAK', 'us_write_api_keys')
        as_write_api_key = self.get_param('THINGSPEAK', 'as_write_api_key')
        channel_ids = self.get_list('THINGSPEAK', 'channel_ids')
        return read_api_keys, us_write_api_keys, as_write_api_key, channel_ids

    def print_params(self):
        """
        Prints out all configuration parameters in a formatted way.
        """
        for section, params in self.config_data.items():
            print(f"[{section}]")
            for key, value in params.items():
                print(f"{key} = {value}")
            print()  # Blank line between sections
            
            
if __name__ == "__main__":
    reader = ConfigReader()
    # print(reader)
    # read_api_keys, us_write_api_keys, as_write_api_key, channel_ids = reader.get_thingspeak_info()
    # print(read_api_keys, us_write_api_keys, as_write_api_key, channel_ids)
    print(reader.get_storagetank_info())