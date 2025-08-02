from django.core.management.base import BaseCommand
from core.tasks import ingest_data  

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Data ingestion started...'))
        
        try:
            result = ingest_data()
            self.stdout.write(self.style.SUCCESS(f'Data ingestion completed. Result: {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data ingestion: {e}'))

