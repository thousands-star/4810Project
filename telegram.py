import asyncio
from aiogram import Bot
from telethon import TelegramClient, events, Button
from aiogram.types import FSInputFile # use for message handler
from dustbinanalysertop import DustbinAnalyser
from dustbin import Dustbin

class TelegramBot:
    """
    A Telegram bot that interacts with users and performs various tasks related to dustbin monitoring and analysis.
    """
    def __init__(self, token, api_id, api_hash, interval, alert_frequency, write_api_key, dustbin_list:list[Dustbin]):
        # Parameter
        self.interval = interval
        self.alert_frequency = alert_frequency
        self.count = 0
        self.dustbin_list = dustbin_list
        self.chat_ids = set()  # Store chat_ids of users who interact with the bot

        # Set up telegram bot and dustbin analyzer
        self.bot = Bot(token)
        self.client = TelegramClient('bot', api_id, api_hash).start(bot_token=token)
        self.data_analyser = DustbinAnalyser(write_api_key, dustbin_list)

        # Register event handlers
        self.register_handlers()


    """
    Handlers
    """
    # This function is responsible detecting different command send from telegram client, and run necessary handler 
    def register_handlers(self):
        # Registering the event handlers
        self.client.on(events.NewMessage(pattern='Send me to real-time'))(self.realTimeGraph)
        self.client.on(events.NewMessage(pattern='/start'))(self.main_menu)
        self.client.on(events.NewMessage(pattern='Back!'))(self.main_menu)
        self.client.on(events.NewMessage(pattern='Send me a data analysis'))(self.sendDataAnalysis)
        self.client.on(events.NewMessage(pattern='Send me a graph of current fullness!'))(self.sendGraph)

    # This function responsible for sending the analyzed data to the telegram bot 
    async def sendDataAnalysis(self, event):
        with open('analysis.txt', 'r') as file:
            # Read the entire file content into a string
            message = file.read()
            await self.bot.send_message(event.chat_id, message)

    # This function responsible for sending the analyzed graph to the telegram bot 
    async def sendGraph(self, event):
        await self.bot.send_message(event.chat_id, "Here is the graph of the current fullness:")
        file_to_send = FSInputFile("dustbin_fullness.png")
        await self.bot.send_document(event.chat_id, file_to_send)

    # This function responsible for sending a web-based real-time analyzed data 
    async def realTimeGraph(self, event):
        await event.respond(
            'Link to real-time graphing:',
            buttons=[
                [Button.url('ThingSpeak', 'https://thingspeak.com/channels/2622766')],
            ]
        )

    # This function responsible for creating button to display a menu list in the telegram bot 
    async def main_menu(self, event):
        self.chat_ids.add(event.chat_id)  # Store chat_id
        await event.respond(
            'Welcome! Choose an option:',
            buttons=[
                [Button.text('Send me to real-time')],
                [Button.text('Send me a data analysis')],
                [Button.text('Send me a graph of current fullness!')]
            ]
        )


    """
    Dustbin Analyser(To get the lastest data and plot)
    """
    async def periodic_task(self):
        while True:
            self.count += 1
            self.data_analyser.getThingspeakData()  # Fetch the latest data
            self.data_analyser.analyseData()        # Analyse the fetched data
            print(self.count)
            print(self.alert_frequency)
            print(self.chat_ids)
            if self.count % self.alert_frequency == 0:  # Prevent spamming alerts
                for i in range(self.data_analyser.getDustbinNumber()):
                    # Print the latest distance data for each dustbin
                    # print(f"Dustbin {i+1} latest distance: {data_analyser.raw_data_dict[i]['y'][-1]} cm")
                    fullness = self.data_analyser.getDustbinFullness()[i]
                    if fullness >= 80:
                        message = f"Alert: Dustbin {self.dustbin_list[i].get_tag()} is {fullness:.2f}% full. Please empty it."
                        for chat_id in self.chat_ids:
                            await self.bot.send_message(chat_id, message)
            self.data_analyser.updateThingspeak()   # Update Thingspeak with the analysed data
            self.data_analyser.plotFullness()       # Plot the latest data
            await asyncio.sleep(self.interval)

    """
    Bot operations 
    """
    # This function is responsible to start listening from the telegram client 
    async def run(self):
        # Start the client in the main thread
        await self.client.start()
        await self.client.run_until_disconnected()



# Main
if __name__ == "__main__":
    # Telegram bot parameters
    token = "7368549794:AAG5QqG5zM-PwhHze7F09wsltwV8z34Lv3A" # The bot token provided by BotFather
    api_id = '26493375' # API ID from telegram 
    api_hash = 'f0615ce015c8e92091a5513a58d8b712' # API hash from telegram 

    # Thinkspeak parameters
    read_api_key = ['FR97G4Z3JFM9LK4Z','DT76O8OQ5F0ZWLXW','CJGXBTKXSZDJHPU2','XG4JT6TJMMCCNK5G'] # API key for retriving data from thinkspeak (raw data)
    write_api_key = "NVF9Q3QGYMYRLCKJ" # API key for writing data into thinkspeak (analyzed data)
    channel_id = [2623642, 2615870, 2623647, 2623708] # channel id for retriving data from thinkspeak (raw data)

    # User Prompt Parameters
    interval = int(input("Enter the update interval (in seconds): "))
    alert_frequency = int(input("Enter the alert frequency (every alert_frequency*interval seconds): "))
    dustbin_num = int(input("Enter the number of dustbins deployed: "))
   
    dustbin_list: list[Dustbin] = []
    for i in range(dustbin_num):
        url = f"https://api.thingspeak.com/channels/{channel_id[i]}/fields/1/last.json?api_key={read_api_key[i]}&status=true"
        depth = float(input(f"Please enter the depth of dustbin {i+1}: "))
        tag = input(f"Please enter the tag of dustbin {i+1}: ")
        dustbin_list.append(Dustbin(depth, tag, url))

    # Create an instance of the TelegramBot class
    bot = TelegramBot(token, api_id, api_hash, interval, alert_frequency, write_api_key, dustbin_list)

    # Create the asyncio loop
    loop = asyncio.get_event_loop()

    # Scheduled loop, for the bot and the periodic task to run asynchrounously 
    loop.create_task(bot.run())
    loop.create_task(bot.periodic_task())

    # Start the loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        loop.close()
