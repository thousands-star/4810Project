import requests
import time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from config_reader import ConfigReader

class Dustbin:
    """
    A dustbin class for the purpose of tracking fullness of a dustbin.
    """
    def __init__(self, depth:int, tag: str, url: str=""):
        """
        Initializes a new instance of the Dustbin class.

        Args:
            depth (float): The depth of the dustbin.
            tag (str): The tag(name) of the dustbin.
            url (str, optional): The URL of the dustbin object where data of raw distance from ultrasonic sensor is stored. 
                                 Defaults to an empty string.

        Returns:
            None
        """
        self.depth = depth
        self.tag = tag
        self.url = url
        
    def get_depth(self):
        """
        Returns the depth of the dustbin.

        Returns:
            depth (int): The depth of the dustbin.
        """
        return self.depth
    
    def get_tag(self):
        """
        Returns the tag of the dustbin.

        Returns:
            tag (str): The tag of the dustbin.
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
            current_distance (float): The current distance from where ultrasonic sensor is placed to the obstacle(trash) detected .

        Returns:
            fullness (float): The fullness percentage restricted from 0 - 100 %
        """
        fullness = (self.depth - current_distance)/self.depth * 100
        if fullness < 0:
            fullness = 0
        elif fullness > 100:
            fullness = 100
        return fullness
    
class DustbinAnalyser:
    """
    A Dustbin Analsyser that interprets the raw data collected from the ultrasonic sensor, performs analysis and
    generates useful message (e.g. a graph of the fullness, message to the telegram bot).
    """
    def __init__(self, configReader:ConfigReader):
        """
        Initializes a DustbinAnalyser object.

        Args:
            dustbin_list (list[Dustbin]): A list of Dustbin objects.

        Returns:
            None
        """
        self.write_api_key = configReader.get_param("THINGSPEAK", "write_api_key")  # The API key used to write analysed data to ThingSpeak
        read_api_keys, write_api_key, channel_ids = configReader.get_thingspeak_info()
        dustbins_info = configReader.get_dustbin_info()
        dustbin_list = []
        # Prepare the dustbin objects
        for i, dustbin_info in enumerate(dustbins_info):
            url = f"https://api.thingspeak.com/channels/{channel_ids[i]}/fields/1/last.json?api_key={read_api_keys[i]}&status=true"
            depth = dustbin_info['depth']
            tag = dustbin_info['tag']
            dustbin_list.append(Dustbin(depth, tag, url))
            
        self.raw_data_dict: dict[int, list] = {}        # A dictionary to store the raw data from all the dustbins
        self.dustbin_num = len(dustbin_list)
        for i in range(self.dustbin_num):
            self.raw_data_dict[i] = []
        self.dustbin_list = dustbin_list                # A list of Dustbin objects         
        self.dustbin_fullness = [0]*self.dustbin_num    # A list to store the fullness of each dustbin
            
    def getThingspeakData(self):
        """
        Retrieves data from the Thingspeak API for each dustbin in the dustbin_list.

        This function iterates over each dustbin in the dustbin_list and retrieves the data from the Thingspeak API.
        It sends a GET request to the URL of each dustbin and checks the response status code. If the status code
        is 200, it parses the JSON response and extracts the distance value. The distance value is then appended
        to the raw_data_dict for the corresponding dustbin for further analysis.

        Args:
            None
            
        Returns:
            None
        """
        for i in range(self.dustbin_num):
            print(f"Retrieving data for plot {i+1}...")
            response = requests.get(self.dustbin_list[i].get_url())
            if response.status_code == 200:
                # print(f"Data for plot {i+1} retrieved successfully, status code: {response.status_code}")
                json_data = response.json()
                distance = float(json_data["field1"])
                # check if the distance in a sensible range
                dustbin_dept = self.dustbin_list[i].get_depth()
                if distance > 1.05*dustbin_dept:
                    # Not appending the distance to the raw data list, 
                    # this is due to the dustbin too full usually
                    # means that sensor is not working properly
                    print(f"Distance detected for dustbin {self.dustbin_list[i].get_tag()} is out of range: {distance:.2f} cm")  
                else:
                    self.raw_data_dict[i].append(distance) 
                    print(self.raw_data_dict[i])
            else:
                print(f"Failed to retrieve data for plot {i}, status code: {response.status_code}")
    
    def analyseData(self):
        """
        Analyzes the data for each dustbin and calculates the fullness.

        This function iterates over each dustbin in the `dustbin_list` and calculates the fullness
        based on the latest data point. The fullness is calculated by calling the `calculate_fullness`
        method of the corresponding `Dustbin` object. The calculated fullness is then stored in the
        `dustbin_fullness` list.

        Args:
            None

        Returns:
            None
        """
        for i in range(self.dustbin_num):
            current_distance = self.raw_data_dict[i][-1]  # use the latest data for fullness calculation
            fullness = self.dustbin_list[i].calculate_fullness(current_distance)
            self.dustbin_fullness[i] = fullness
        
    
    def updateThingspeak(self):
        """
        Updates the Thingspeak channel with the latest dustbin fullness data
        and creates a text file named "analysis.txt" that writes the fullness information for each dustbin.
        The file includes the fullness percentage for each dustbin, 
        as well as the dustbin with the highest and lowest fullness.

        Args:
            None

        Returns:
            None
        """
        RequestToThingspeak = f"https://api.thingspeak.com/update?api_key={self.write_api_key}" 
        # add the data for each dustbin to the request for simultaneous update of all dustbins
        for i in range(self.dustbin_num):
            RequestToThingspeak += f"&field{i+1}={self.dustbin_fullness[i]}"    
        
        ### for testing purposes
        request = requests.get(RequestToThingspeak)
        print(request.text)
        
        # create a txt file for telegram sending
        # construct data for writing to the txt file
        data = []
        data.append(f"Fullness for Each Dustbin")
        for i in range(self.dustbin_num):
            data.append(f"Dustbin {self.dustbin_list[i].get_tag()}: {self.dustbin_fullness[i]:.2f}%")
        data.append("Up to Now:")
        max_index = self.dustbin_fullness.index(max(self.dustbin_fullness))
        min_index = self.dustbin_fullness.index(min(self.dustbin_fullness))
        data.append(f"Most occupied: Dustbin {self.dustbin_list[max_index].get_tag()} - {max(self.dustbin_fullness):.2f}%")
        data.append(f"Least occupied: Dustbin {self.dustbin_list[min_index].get_tag()} - {min(self.dustbin_fullness):.2f}%")
        
        # write the data to the txt file
        file_path = "analysis.txt"
        data_with_newlines = [line + "\n" for line in data]
        with open(file_path, 'w') as file:
            file.writelines(data_with_newlines)
    
    def plotFullness(self):
        """
        Plots the fullness of each dustbin in a bar chart.

        This function generates a bar chart to visualize the current fullness of each dustbin.
        The bar colors are determined based on the following criteria:
        - If the fullness is above 80%, the bar color is set to 'red'.
        - If the fullness is in the range of 60 - 80 %, the bar color is set to 'orange'.
        - Otherwise (below 60 %), the bar color is set to 'green'.

        Args:
            None

        Returns:
            None
        """
        dustbin_tags = [f"{self.dustbin_list[i].get_tag()}" for i in range(self.dustbin_num)]
        
        # Set the bar colors accordingly
        bar_colors = []
        for fullness in self.dustbin_fullness:
            if fullness > 80:
                bar_colors.append('red')
            elif fullness > 60:
                bar_colors.append('orange')
            else:
                bar_colors.append('green')
        
        plt.clf()                                       # Clear the current figure to update with new data
        plt.bar(dustbin_tags, self.dustbin_fullness, color=bar_colors)
        plt.xlabel('Dustbin')
        plt.ylabel('Current Fullness (%)')
        plt.title('Fullness for Each Dustbin')
        plt.ylim(0, 100)                                # Set the y-axis limit to 100%
        # Add grid for better visibility
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        # Create custom legend handles
        red_patch = mpatches.Patch(color='red', label='Above 80% (High Capacity)')
        orange_patch = mpatches.Patch(color='orange', label='61% - 80% (Moderate Capacity)')
        green_patch = mpatches.Patch(color='green', label='0% - 60% (Low Capacity)')
        # Add the legend to the plot
        plt.legend(handles=[red_patch, orange_patch, green_patch], title="Fullness Levels")
        plt.savefig("dustbin_fullness.png")             # Save the plot to a png file    
        
    def getDustbinNumber(self):
        """
        Returns the number of dustbins.

        Returns:
            dustbin_num (int): The number of dustbins.
        """
        return self.dustbin_num
    
    def getDustbinFullness(self):
        """
        Returns the fullness of the dustbin.

        Returns:
            dustbin_fullness (list): A list of floats representing the fullness of each dustbin.
        """
        return self.dustbin_fullness

    

if __name__ == "__main__":
    # for reading and writing to the thinkspeak
    # read_api_key and channle_id will set the url for each dustbin
    read_api_key = ['FR97G4Z3JFM9LK4Z','DT76O8OQ5F0ZWLXW','CJGXBTKXSZDJHPU2','XG4JT6TJMMCCNK5G']
    # read_api_key = ['FR97G4Z3JFM9LK4Z','DT76O8OQ5F0ZWLXW','XG4JT6TJMMCCNK5G']
    channel_id = [2623642, 2615870, 2623647, 2623708]
    dustbin_num = int(input("Please enter the number of dustbin: "))
    dustbin_list: list[Dustbin] = []
    for i in range(dustbin_num):
        url = f"https://api.thingspeak.com/channels/{channel_id[i]}/fields/1/last.json?api_key={read_api_key[i]}&status=true"
        depth = int(input(f"Please enter the depth of dustbin {i+1}: "))
        tag = input(f"Please enter the tag of dustbin {i+1}: ")
        dustbin_list.append(Dustbin(depth, tag, url))
        
    write_api_key = "NVF9Q3QGYMYRLCKJ"
    data_analyser = DustbinAnalyser(write_api_key, dustbin_list)
    
    try:
        while True:
            data_analyser.getThingspeakData()  # Fetch the latest data
            data_analyser.analyseData()        # Analyse the fetched data
            for i in range(len(dustbin_list)):
                # Print the latest distance data for each dustbin
                print(f"Raw distance for {dustbin_list[i].get_tag()}: {data_analyser.raw_data_dict[i][-1]} cm")
                print(f"Fullness for {dustbin_list[i].get_tag()}: {data_analyser.dustbin_fullness[i]:.2f}%")
            data_analyser.updateThingspeak()   # Update Thingspeak with the analysed data
            data_analyser.plotFullness()       # Plot the latest data
            time.sleep(15)                     # Wait for 15 seconds before the next update
    except KeyboardInterrupt:
        exit()


