from server import TelegramBot
import asyncio
from config_reader import ConfigReader

# Main
if __name__ == "__main__":
    # Initiate a config_reader
    config_reader = ConfigReader()
    # Create an instance of the TelegramBot class
    # set exist_analyser to False if you dont want to use stockAnalyser
    bot = TelegramBot(configReader = config_reader, exist_analyser=True)

    print("Setup Completed!")

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
