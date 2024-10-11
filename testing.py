# Open the file for reading
with open('fullness.txt', 'r') as file:
    for line in file:
        line = line.strip()
        name, fullness = line.split()
        # Convert fullness to a float
        fullness = float(fullness)
        # Print the results (or do something with them)
        print(f"Item: {name}, Fullness: {fullness}")
