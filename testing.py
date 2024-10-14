import joblib
import numpy as np

model_filename = "./model/model4.pkl"
# Load the model from the file
loaded_model = joblib.load(model_filename)
print("Model loaded successfully.")
# Use the loaded model to make predictions
new_input = np.array([[12 * 60, 3]])  # Example input for 12 PM on Thursday
predicted_rate_of_change = loaded_model.predict(new_input)
print(f"Predicted rate of change: {predicted_rate_of_change[0]:.4f} units/minute")
current_inventory_level = 100  # Example current inventory level
minute_of_day = 12 * 60  # 12 PM in minutes from start of day
weekday = 3  # Thursday
time_elapsed = 0  # Track total time until depletion
# Run a while loop until the inventory is depleted
while current_inventory_level > 0:
    # Predict the rate of change for the current time and weekday
    new_input = np.array([[minute_of_day, weekday]])
    predicted_rate_of_change = loaded_model.predict(new_input)[0]
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
