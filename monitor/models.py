from django.db import models

from domain.models import Record


class Monitor(models.Model):
    MONITOR_TYPE_CHOICES = (
        (1, "tcp"),
        (2, "http"),
    )
    MONITOR_STATUS_CHOICES = (
        (1, 'enable'),
        (2, 'disable'),
    )

    record = models.ForeignKey(Record)
    type = models.PositiveSmallIntegerField(choices=MONITOR_TYPE_CHOICES)
    status = models.PositiveSmallIntegerField(choices=MONITOR_STATUS_CHOICES)
    frequency = models.PositiveSmallIntegerField()
    allowable_failure_times = models.PositiveIntegerField()
    content = models.TextField()
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)