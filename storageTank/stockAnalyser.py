import requests
import time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
try:
    from config_reader import ConfigReader
except:
    import sys
    import os
    # Add the parent directory to the system path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config_reader import ConfigReader


class StorageTank:
    """
    A class for the purpose of tracking fullness of storage tank.
    """
    def __init__(self, depth:int, tag: str, url: str=""):
        """
        Initializes a new instance of the stockAnalyzer class.

        Args:
            depth (float): The depth of the storage tank.
            tag (str): The tag(name) of the storage tank.
            url (str, optional): The URL of the storage tank object where data of raw distance from ultrasonic sensor is stored. 
                                 Defaults to an empty string.

        Returns:
            None
        """
        self.depth = depth
        self.tag = tag
        self.url = url
        
    def get_depth(self):
        """
        Returns the depth of the storage tank.

        Returns:
            depth (int): The depth of the storage tank.
        """
        return self.depth
    
    def get_tag(self):
        """
        Returns the tag of the storage tank.

        Returns:
            tag (str): The tag of the storage tank.
        """
        return self.tag
    
    def get_url(self):
        """
        Returns the URL of the object.

        Returns:
            url (str): The URL of the object.
        """
        return self.url
    
    def set_depth(self, depth):
        """
        Set the depth of the object.

        Parameters:
            depth (int): The new depth value.

        Returns:
            None
        """
        self.depth = depth
    
    def set_tag(self, tag):
        """
        Set the tag of the object.

        Parameters:
            tag (str): The new tag value.

        Returns:
            None
        """ 
        self.tag = tag
    
    def set_url(self, url):
        """
        Set the URL of the object.

        Parameters:
            url (str): The new URL value.

        Returns:
            None
        """
        self.url = url
        
    def calculate_fullness(self, current_distance):
        """
        Calculate the fullness of the object based on the current distance detected from ultrasonic sensor.

        Args:
            current_distance (float): The current distance from where ultrasonic sensor is placed to the obstacle(stock) detected .

        Returns:
            fullness (float): The fullness percentage restricted from 0 - 100 %
        """
        current_distance = min(self.depth, current_distance)  # Ensure the distance does not exceed the depth
        fullness = (self.depth - current_distance)/self.depth * 100
        return fullness
    
class StockAnalyser:
    """
    A Stock Analsyser that interprets the raw data collected from the ultrasonic sensor, performs analysis and
    generates useful message (e.g. a graph of the fullness, message to the telegram bot).
    """
    def __init__(self, configReader:ConfigReader):
        """
        Initializes a StockAnalyser object.

        Args:
            configReader (ConfigReader): A ConfigReader object

        Returns:
            None
        """
        read_api_keys, _, as_write_api_key, channel_ids = configReader.get_thingspeak_info()
        self.write_api_key = as_write_api_key  # The API key used to write analysed data to ThingSpeak
        storagetank_info = configReader.get_storagetank_info()
        self.storagetank_list: list[StorageTank] = []
        # Prepare the dustbin objects
        for i, tank_info in enumerate(storagetank_info):
            url = f"https://api.thingspeak.com/channels/{channel_ids[i]}/fields/1/last.json?api_key={read_api_keys[i]}&status=true"
            depth = tank_info['depth']
            tag = tank_info['tag']
            self.storagetank_list.append(StorageTank(depth, tag, url))
        self.raw_data_dict: dict[int, list] = {}        # A dictionary to store the raw data from all the dustbins
        self.storagetank_num = len(self.storagetank_list)
        for i in range(self.storagetank_num):
            self.raw_data_dict[i] = []  
        self.storagetank_fullness = [0]*self.storagetank_num    # A list to store the fullness of each dustbin
            
    def getThingspeakData(self):
        """
        Retrieves data from the Thingspeak API for each storge tank in the storagetank_list.

        This function iterates over each tank in the storagetank_list and retrieves the data from the Thingspeak API.
        It sends a GET request to the URL of each tank and checks the response status code. If the status code
        is 200, it parses the JSON response and extracts the distance value. The distance value is then appended
        to the raw_data_dict for the corresponding tank dustbin for further analysis.

        Args:
            None
            
        Returns:
            None
        """
        for i in range(self.storagetank_num):
            print(f"Retrieving data for plot {i+1}...")
            response = requests.get(self.storagetank_list[i].get_url())
            if response.status_code == 200:
                # print(f"Data for plot {i+1} retrieved successfully, status code: {response.status_code}")
                json_data = response.json()
                # print(distance)
                distance = float(json_data["field1"])
                # check if the distance in a sensible range
                tank_dept = self.storagetank_list[i].get_depth()
                if distance > 1.05*tank_dept:
                    # Not appending the distance to the raw data list, 
                    # this is due to the dustbin too full usually
                    # means that sensor is not working properly
                    print(f"Distance detected for tank {self.storagetank_list[i].get_tag()} is out of range: {distance:.2f} cm")  
                else:
                    self.raw_data_dict[i].append(distance) 
                    print(self.raw_data_dict[i])
            else:
                print(f"Failed to retrieve data for plot {i}, status code: {response.status_code}")
    
    def analyseData(self):
        """
        Analyzes the data for each storage tank and calculates the fullness.

        This function iterates over each tank in the `storagetank_list` and calculates the fullness
        based on the latest data point. The fullness is calculated by calling the `calculate_fullness`
        method of the corresponding `Dustbin` object. The calculated fullness is then stored in the
        `storagetank_fullness` list.
        Args:
            None

        Returns:
            None
        """
        # print("storage_tank num: ", self.storagetank_num)
        for i in range(self.storagetank_num):
            current_distance = self.raw_data_dict[i][-1]  # use the latest data for fullness calculation
            fullness = self.storagetank_list[i].calculate_fullness(current_distance)
            self.storagetank_fullness[i] = fullness
        
    
    def updateThingspeak(self):
        """
        Updates the Thingspeak channel with the latest tank fullness data
        and creates a text file named "analysis.txt" that writes the fullness information for each tank
        The file includes the fullness percentage for each storage tank, 
        as well as the storage tank with the highest and lowest fullness.

        Args:
            None

        Returns:
            None
        """
        RequestToThingspeak = f"https://api.thingspeak.com/update?api_key={self.write_api_key}" 
        # add the data for each dustbin to the request for simultaneous update of all dustbins
        for i in range(self.storagetank_num):
            RequestToThingspeak += f"&field{i+1}={self.storagetank_fullness[i]}"    
        
        ### for testing purposes
        request = requests.get(RequestToThingspeak)
        print(request.text)
        
        # create a txt file for telegram sending
        # construct data for writing to the txt file
        data = []
        data.append(f"Fullness for Each Storage Tank")
        for i in range(self.storagetank_num):
            data.append(f"Storage Tank {self.storagetank_list[i].get_tag()}: {self.storagetank_fullness[i]:.2f}%")
        max_index = self.storagetank_fullness.index(max(self.storagetank_fullness))
        min_index = self.storagetank_fullness.index(min(self.storagetank_fullness))
        data.append(f"Note: Highest stock level in Storage Tank {self.storagetank_list[max_index].get_tag()} - {max(self.storagetank_fullness):.2f}%. Check for potential expiration.")
        data.append(f"Stock replenishment needed for Storage Tank {self.storagetank_list[min_index].get_tag()} - {min(self.storagetank_fullness):.2f}% remaining.")

        # write the data to the txt file
        file_path = "analysis.txt"
        data_with_newlines = [line + "\n" for line in data]
        with open(file_path, 'w') as file:
            file.writelines(data_with_newlines)
    
    def plotFullness(self):
        """
        Plots the fullness of each tank in a bar chart.

        This function generates a bar chart to visualize the current fullness of each storage tank.
        The bar colors are determined based on the following criteria:
        - If the fullness is above 75%, the bar color is set to 'green'.
        - If the fullness is in the range of 30 - 75 %, the bar color is set to 'orange'.
        - Otherwise (below 30 %), the bar color is set to 'red'.

        Args:
            None

        Returns:
            None
        """
        tank_tags = [f"{self.storagetank_list[i].get_tag()}" for i in range(self.storagetank_num)]
        
        # Set the bar colors accordingly
        bar_colors = []
        for fullness in self.storagetank_fullness:
            if fullness > 75:
                bar_colors.append('green')
            elif fullness > 30:
                bar_colors.append('orange')
            else:
                bar_colors.append('red')
        
        plt.clf()                                       # Clear the current figure to update with new data
        plt.bar(tank_tags, self.storagetank_fullness, color=bar_colors)
        plt.xlabel('Storage Tank')
        plt.ylabel('Current Fullness (%)')
        plt.title('Fullness for Each Tank')
        plt.ylim(0, 100)                                # Set the y-axis limit to 100%
        # Add grid for better visibility
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        # Create custom legend handles
        green_patch = mpatches.Patch(color='green', label='Above 75% (High Capacity)')
        orange_patch = mpatches.Patch(color='orange', label='30% - 75% (Moderate Capacity)')
        red_patch = mpatches.Patch(color='red', label='0% - 30% (Low Capacity)')
        # Add the legend to the plot
        plt.legend(handles=[green_patch, orange_patch, red_patch], title="Fullness Levels")
        plt.savefig("storagetank_fullness.png")             # Save the plot to a png file    
    

if __name__ == "__main__":
    # Read info using config_reader
    config_reader = ConfigReader()
    data_analyser = StockAnalyser(config_reader)
    
    try:
        while True:
            data_analyser.getThingspeakData()  # Fetch the latest data
            data_analyser.analyseData()        # Analyse the fetched data
            tank_list = data_analyser.storagetank_list
            for i in range(len(tank_list)):
                # Print the latest distance data for each dustbin
                print(f"Raw distance for {tank_list[i].get_tag()}: {data_analyser.raw_data_dict[i][-1]} cm")
                print(f"Fullness for {tank_list[i].get_tag()}: {data_analyser.storagetank_fullness[i]:.2f}%")
            data_analyser.updateThingspeak()   # Update Thingspeak with the analysed data
            data_analyser.plotFullness()       # Plot the latest data
            time.sleep(15)                     # Wait for 15 seconds before the next update
    except KeyboardInterrupt:
        exit()


