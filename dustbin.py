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
