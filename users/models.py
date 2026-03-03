from django.db import models

# models.py
class Candidate(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()  # <-- Add this
    job_description = models.TextField()
    interview_start_time = models.DateTimeField(null=True, blank=True)
    interview_end_time = models.DateTimeField(null=True, blank=True)
    tab_switch_count = models.IntegerField(default=0)
    is_disqualified = models.BooleanField(default=False)
    disqualification_reason = models.TextField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class InterviewResponse(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    score = models.IntegerField(null=True, blank=True)


from django.db import models

class RegisteredUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    password = models.CharField(max_length=100)  # store plain for demo; use hashing in prod!
    image = models.ImageField(upload_to='user_images/')
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
