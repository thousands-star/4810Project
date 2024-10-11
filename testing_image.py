import requests

# Replace 'http://your_raspberry_pi_ip:5000/get-image' with your actual Raspberry Pi's IP
url = 'http://192.168.137.108:5000/get-image'
response = requests.get(url)

if response.status_code == 200:
    with open('downloaded_image.png', 'wb') as f:
        f.write(response.content)
    print("Image downloaded successfully!")
else:
    print(f"Failed to download image. Status code: {response.status_code}")
