import asyncio
from aiogram import Bot
from telethon import TelegramClient, events, Button
from aiogram.types import FSInputFile # use for message handler
from dustbinanalysertop import DustbinAnalyser
from dustbin import Dustbin
from config_reader import ConfigReader

class TelegramBot:
    """
    A Telegram bot that interacts with users and performs various tasks related to dustbin monitoring and analysis.
    """
    def __init__(self, configReader: ConfigReader, dustbin_analyser:DustbinAnalyser=None):
        # Parameter
        token = configReader.get_param('TELEGRAM', 'token')
        api_id = configReader.get_param('TELEGRAM', 'api_id')
        api_hash = configReader.get_param('TELEGRAM', 'api_hash')
        self.interval = int(configReader.get_param('TELEGRAM', 'interval'))
        self.alert_frequency = int(configReader.get_param('TELEGRAM', 'alert_frequency'))
        self.count = 0
        self.chat_ids = set()  # Store chat_ids of users who interact with the bot

        # Set up telegram bot and dustbin analyzer
        print(token)
        self.bot = Bot(token)
        self.client = TelegramClient('bot', api_id, api_hash).start(bot_token=token)
        if(dustbin_analyser == None):
            self.exist_analyser = 0
        else:
            self.data_analyser = dustbin_analyser

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
            if self.exist_analyser == 0:
                print("No data analyser available.")
            else:
                self.data_analyser.getThingspeakData()  # Fetch the latest data
                self.data_analyser.analyseData()        # Analyse the fetched data
                
                if self.count % self.alert_frequency == 0:  # Prevent spamming alerts
                    for i in range(self.data_analyser.getDustbinNumber()):
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