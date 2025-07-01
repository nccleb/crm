# queuestat/management/commands/monitor_queue.py
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from queuestat.views import AgentDetailsView, alert_manager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Continuously monitor UCM6202 queue for unanswered calls'
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.stats = {
            'checks_performed': 0,
            'alerts_sent': 0,
            'errors': 0,
            'start_time': None
        }
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.stdout.write(
            self.style.WARNING('\nReceived shutdown signal. Stopping monitor...')
        )
        self.running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Monitoring interval in seconds (default: 30)'
        )
        
        parser.add_argument(
            '--lookback',
            type=int, 
            default=30,
            help='Minutes to look back for calls (default: 30)'
        )
        
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (less verbose output)'
        )
        
        parser.add_argument(
            '--max-errors',
            type=int,
            default=10,
            help='Maximum consecutive errors before stopping (default: 10)'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        lookback_minutes = options['lookback']
        daemon_mode = options['daemon']
        max_errors = options['max_errors']
        
        self.stats['start_time'] = datetime.now()
        consecutive_errors = 0
        
        if not daemon_mode:
            self.stdout.write(
                self.style.SUCCESS(
                    f'🚀 Starting UCM6202 Queue Monitor\n'
                    f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                    f'⏱️  Monitoring interval: {interval} seconds\n'
                    f'🔍 Lookback period: {lookback_minutes} minutes\n'
                    f'📧 Alert recipients: {len(getattr(settings, "CALL_ALERT_RECIPIENTS", []))} configured\n'
                    f'⚠️  Max consecutive errors: {max_errors}\n'
                    f'🛑 Press Ctrl+C to stop\n'
                    f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                )
            )
        
        agent_view = AgentDetailsView()
        
        try:
            while self.running:
                try:
                    # Calculate time range for monitoring
                    now = datetime.now()
                    start_time = now.strftime('%Y-%m-%d ')
                    end_time = now.strftime('%Y-%m-%d ')
                    
                    if not daemon_mode:
                        self.stdout.write(f'[{now.strftime("%H:%M:%S")}] 🔍 Checking queue status...')
                    
                    # Get API authentication
                    cookie = agent_view.get_api_cookie()
                    if not cookie:
                        consecutive_errors += 1
                        error_msg = f'❌ Failed to authenticate with UCM6202 API (Error {consecutive_errors}/{max_errors})'
                        
                        if daemon_mode:
                            logger.error(error_msg)
                        else:
                            self.stdout.write(self.style.ERROR(error_msg))
                        
                        if consecutive_errors >= max_errors:
                            raise Exception(f"Too many consecutive authentication failures ({max_errors})")
                        
                        time.sleep(interval)
                        continue
                    
                    # Get current queue data
                    queue_data = agent_view.get_queue_data(cookie, start_time, end_time, '', '')
                    
                    
                    
                    # Reset error counter on successful API call
                    consecutive_errors = 0
                    self.stats['checks_performed'] += 1
                    
                    # Check for alerts
                    alerts = alert_manager.check_queue_for_alerts(queue_data, "Background Monitor")
                    
                    if alerts:
                        alert_count = len(alerts)
                        self.stats['alerts_sent'] += alert_count
                        
                        if not daemon_mode:
                            self.stdout.write(
                                self.style.WARNING(f'🚨 Found {alert_count} alert(s) - sending notifications...')
                            )
                        
                        # Send email alerts
                        for alert in alerts:
                            try:
                                success = alert_manager.send_alert_email(alert)
                                if not daemon_mode:
                                    if success:
                                        self.stdout.write(
                                            self.style.SUCCESS(f'  ✅ Alert sent: {alert["type"]} for {alert["caller_number"]}')
                                        )
                                    else:
                                        self.stdout.write(
                                            self.style.ERROR(f'  ❌ Failed to send alert for {alert["caller_number"]}')
                                        )
                            except Exception as e:
                                logger.error(f"Failed to send alert: {str(e)}")
                                if not daemon_mode:
                                    self.stdout.write(
                                        self.style.ERROR(f'  ❌ Alert send error: {str(e)}')
                                    )
                    else:
                        if not daemon_mode:
                            active_calls = len([item for item in queue_data if item.get('agent', {}).get('agent') != 'NONE'])
                            self.stdout.write(f'✅ Queue OK - {active_calls} active calls, no alerts needed')
                    
                    # Show periodic stats
                    if not daemon_mode and self.stats['checks_performed'] % 10 == 0:
                        self.show_stats()
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    consecutive_errors += 1
                    self.stats['errors'] += 1
                    
                    error_msg = f'❌ Monitor error ({consecutive_errors}/{max_errors}): {str(e)}'
                    
                    if daemon_mode:
                        logger.error(error_msg)
                    else:
                        self.stdout.write(self.style.ERROR(error_msg))
                    
                    if consecutive_errors >= max_errors:
                        raise Exception(f"Too many consecutive errors ({max_errors})")
                
                # Wait for next check
                if self.running:
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'💥 Monitor stopped due to error: {str(e)}')
            )
            logger.error(f"Queue monitor stopped: {str(e)}")
            sys.exit(1)
        finally:
            self.show_final_stats()
    
    def show_stats(self):
        """Show monitoring statistics"""
        uptime = datetime.now() - self.stats['start_time']
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 Monitor Statistics:\n'
                f'   ⏱️  Uptime: {hours}h {minutes}m\n'
                f'   🔍 Checks performed: {self.stats["checks_performed"]}\n'
                f'   🚨 Alerts sent: {self.stats["alerts_sent"]}\n'
                f'   ❌ Errors: {self.stats["errors"]}\n'
            )
        )
    
    def show_final_stats(self):
        """Show final statistics on shutdown"""
        if not self.stats['start_time']:
            return
            
        uptime = datetime.now() - self.stats['start_time']
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        seconds = int(uptime.total_seconds() % 60)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🏁 UCM6202 Queue Monitor Stopped\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'📈 Final Statistics:\n'
                f'   ⏱️  Total uptime: {hours}h {minutes}m {seconds}s\n'
                f'   🔍 Total checks: {self.stats["checks_performed"]}\n'
                f'   🚨 Total alerts sent: {self.stats["alerts_sent"]}\n'
                f'   ❌ Total errors: {self.stats["errors"]}\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            )
        )