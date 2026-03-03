from django.core.management.base import BaseCommand
from users.models import Candidate, InterviewResponse

class Command(BaseCommand):
    help = 'Clear all interview data from database'

    def handle(self, *args, **kwargs):
        response_count = InterviewResponse.objects.all().count()
        InterviewResponse.objects.all().delete()
        
        candidate_count = Candidate.objects.all().count()
        Candidate.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {candidate_count} candidates and {response_count} responses'
        ))
