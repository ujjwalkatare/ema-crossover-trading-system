import asyncio
from django.core.management.base import BaseCommand
from app.services import main_bot_loop # I've used 'app' since that is your app's name

class Command(BaseCommand):
    help = 'Runs the continuous stock monitoring and Telegram alert bot.'

    def add_arguments(self, parser):
        # Argument for the tickers, comma-separated
        parser.add_argument(
            '--tickers',
            type=str,
            required=True,
            help='A comma-separated list of stock tickers to monitor (e.g., "RELIANCE.NS,TCS.NS").'
        )
        # Argument for the timeframe
        parser.add_argument(
            '--timeframe',
            type=str,
            required=True,
            help='The timeframe for analysis (e.g., "5 Minutes", "1 Hour").'
        )

    def handle(self, *args, **options):
        tickers_str = options['tickers']
        timeframe = options['timeframe']
        
        # Split the string from the command line into a list
        tickers_list = [ticker.strip().upper() for ticker in tickers_str.split(',') if ticker.strip()]
        
        self.stdout.write(self.style.SUCCESS(
            f'Starting stock bot for tickers: {tickers_list} with timeframe: {timeframe}'
        ))
        
        try:
            # Run the asynchronous main loop from your services file
            asyncio.run(main_bot_loop(tickers=tickers_list, timeframe_label=timeframe))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot stopped manually.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred: {e}'))