from django.db import models

# Create your models here.

class Report(models.Model):
    REPORT_TYPES = [
        ('individual', 'Individual Company'),
        ('list', 'List of Companies'),
        ('market', 'Market Sector'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True, null=True)
    submitted_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def url(self):
        return f'/dashboard/report/{self.id}/'
