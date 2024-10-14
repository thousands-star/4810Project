import os
import joblib
import numpy as np
from datetime import datetime
import warnings

# Suppress specific warning
warnings.filterwarnings("ignore", category=UserWarning)

def day_to_index(day):
    # Dictionary to map days to index (Sunday=0, Monday=1, ..., Saturday=6)
    days_of_week = {
        "Sunday": 0,
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6
    }
    # Return the index if the day is valid, otherwise return an error message
    return days_of_week.get(day)

def initialize_model():
    # Get the current working directory
    current_dir = os.getcwd()
    model_dir = os.path.join(current_dir, "model")
    model_list = []
    for model in os.listdir(model_dir):
        loaded_model = joblib.load(os.path.join(model_dir, model))
        model_list.append(loaded_model)
    return model_list
    
def predict_roc(model):
    # Get the current date and time
    now = datetime.now()
    # Extract hour and minute
    current_hour = now.hour
    current_minute = now.minute
    # Get the day of the week (Monday is 0 and Sunday is 6)
    day_of_week = now.strftime("%A")  # Returns the full name of the day (e.g., 'Thursday')
    day = day_to_index(day_of_week)
    # Use the loaded model to make predictions
    new_input = np.array([[current_hour*60+current_minute, day]])  # Example input for 12 PM on Thursday
    predicted_rate_of_change = model.predict(new_input)
    print(f"Predicted rate of change: {predicted_rate_of_change[0]:.4f} units/minute")
    return predicted_rate_of_change[0] 
    
    
def convert_minutes(total_minutes):
    days = total_minutes // (24 * 60)  # Calculate days
    remaining_minutes = total_minutes % (24 * 60)  # Remaining minutes after days are calculated
    hours = remaining_minutes // 60  # Calculate hours
    minutes = remaining_minutes % 60  # Remaining minutes after hours are calculated
    return days, hours, minutes

# Run a while loop until the inventory is depleted
def predict_useuptime(current_inventory_level, model):
    time_elapsed = 0
    now = datetime.now()
    minute_of_day = now.minute + now.hour * 60
    weekday = day_to_index(now.strftime("%A"))
    while current_inventory_level > 0:
        # Predict the rate of change for the current time and weekday
        new_input = np.array([[minute_of_day, weekday]])
        predicted_rate_of_change = model.predict(new_input)[0]
        # If the rate of change is negative, decrease the inventory
        if predicted_rate_of_change < 0:
            current_inventory_level += predicted_rate_of_change
        time_elapsed += 1  # Increment time by one minute
        minute_of_day = (minute_of_day + 1) % 1440  # Update time within the day
        # Update weekday if it is the start of a new day
        if minute_of_day == 0:
            weekday = (weekday + 1) % 7
        # Check if inventory has reached zero or below
        if current_inventory_level <= 0:
            print(f"Inventory depleted after {time_elapsed} minutes.")
            break
        days, hours, minutes = convert_minutes(time_elapsed)
        str_return = f"{days} days, {hours} hours, {minutes} minutes"
    return str_return

def read_fullness():
    with open ('fullness.txt', 'r') as file:
        fullness_list = []
        for line in file:
            line = line.strip()
            name, fullness = line.split()
            # Convert fullness to a float
            fullness = float(fullness)
            # Print the results (or do something with them)
            # print(f"Item: {name}, Fullness: {fullness}")
            fullness_list.append(fullness)
    return fullness_list

if __name__ == "__main__":
    # model_list = initialize_model()
    # roc = predict_roc(model_list[0])
    # print(roc)
    # useuptime = predict_useuptime(50, model_list[1])
    # print(useuptime)
    read_fullness()