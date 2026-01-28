import asyncio
from django.core.management.base import BaseCommand
from app.services import main_bot_loop # Make sure this path is correct for your project

class Command(BaseCommand):
    help = 'Runs the continuous stock monitoring and Telegram alert bot using ticker-timeframe pairs.'

    def add_arguments(self, parser):
        # REMOVED: --tickers and --timeframe arguments
        # ADDED: A single --pairs argument to handle combined data
        parser.add_argument(
            '--pairs',
            type=str,
            required=True,
            help='A comma-separated list of ticker:timeframe pairs (e.g., "RELIANCE.NS:5m,TCS.NS:1h").'
        )

    def handle(self, *args, **options):
        pairs_str = options['pairs']
        
        # This list will hold the parsed configuration for each stock
        stock_configs = []

        # --- NEW LOGIC to parse the pairs string ---
        try:
            # Split the main string by comma to get individual pairs
            pairs_list = [pair.strip() for pair in pairs_str.split(',') if pair.strip()]
            
            for pair in pairs_list:
                # Split each pair by colon to get the ticker and timeframe
                ticker, timeframe = pair.split(':')
                stock_configs.append({
                    'ticker': ticker.strip().upper(), 
                    'timeframe': timeframe.strip()
                })
        except ValueError:
            self.stdout.write(self.style.ERROR(
                f"Invalid format for --pairs argument. Expected 'TICKER:TIMEFRAME,...', but got '{pairs_str}'"
            ))
            return # Exit the command if parsing fails
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred during parsing: {e}"))
            return

        if not stock_configs:
            self.stdout.write(self.style.WARNING('No valid stock pairs found to monitor.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Starting stock bot for {len(stock_configs)} configurations:'
        ))
        for config in stock_configs:
            self.stdout.write(f"- Ticker: {config['ticker']}, Timeframe: {config['timeframe']}")
        
        try:
            # --- UPDATED CALL to your main bot loop ---
            # Pass the list of configuration dictionaries to your bot
            asyncio.run(main_bot_loop(stock_configs=stock_configs))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot stopped manually.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred in the bot loop: {e}'))