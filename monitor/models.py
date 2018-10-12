import uuid
from django.db import models
from django.contrib.auth.models import User

from domain.models import Record


class Monitor(models.Model):
    MONITOR_MTYPE_CHOICES = (
        (1, "tcp"),
        (2, "http"),
    )
    MONITOR_STATUS_CHOICES = (
        (1, 'enable'),
        (2, 'disable'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    mtype = models.PositiveSmallIntegerField(choices=MONITOR_MTYPE_CHOICES)
    status = models.PositiveSmallIntegerField(choices=MONITOR_STATUS_CHOICES)
    frequency = models.PositiveSmallIntegerField()
    allowable_failure_times = models.PositiveIntegerField()
    recent_query_times_threshold = models.PositiveIntegerField()
    content = models.TextField()
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)