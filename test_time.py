from datetime import datetime

# Get the current date and time
now = datetime.now()

# Extract hour and minute
current_hour = now.hour
current_minute = now.minute

# Get the day of the week (Monday is 0 and Sunday is 6)
day_of_week = now.strftime("%A")  # Returns the full name of the day (e.g., 'Thursday')

# Print the results
print(f"Current time: {current_hour}:{current_minute}")
print(f"Today is: {day_of_week}")
