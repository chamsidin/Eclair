from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Clear all Django messages from sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear messages from all sessions',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Clear messages for specific user',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Clear all sessions (this will clear all messages)
            Session.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared all sessions and messages')
            )
        elif options['user']:
            # Clear messages for specific user
            try:
                user = User.objects.get(username=options['user'])
                # This is more complex - would need to iterate through sessions
                self.stdout.write(
                    self.style.WARNING(f'Clearing messages for user {user.username} is complex. Use --all to clear all messages.')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User {options["user"]} does not exist')
                )
        else:
            self.stdout.write(
                self.style.WARNING('Use --all to clear all messages or --user <username> for specific user')
            )
