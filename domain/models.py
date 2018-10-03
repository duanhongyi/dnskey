from django.db import models
from django.contrib.admin.models import User


class Domain(models.Model):
    DOMAIN_TYPE_CHOICES = (
        (1, "stub"),
        (1, "primary"),
        (1, "secondary"),
    )
    user = models.ForeignKey(User)
    type = models.PositiveSmallIntegerField(choices=DOMAIN_TYPE_CHOICES)
    name = models.CharField(length=255, db_index=True, unique=True)
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)


class Region(models.Model):
    state = models.TextField()
    province = models.TextField()
    city = models.TextField()
    zone = models.TextField()
    start_address = models.DecimalField(db_index=True)
    end_address = models.DecimalField(db_index=True)
    description = models.TextField(blank=True)


class Record(models.Model):
    RECORD_TYPE_CHOICES = (
        (1, 'A'),
        (2, 'NS'),
        (5, 'CNAME'),
        (15, 'MX'),
        (16, 'TXT'),
        (28, 'AAAA'),
        (33, 'SRV'),
    )

    RECORD_STATUS_CHOICES = (
        (0, 'error'),
        (1, 'enable'),
        (2, 'disable'),
    )

    domain = models.ForeignKey(Domain)
    region_name = models.CharField(length=32, db_index=True)
    name = models.CharField(length=255, db_index=True, unique=True)
    type = models.PositiveSmallIntegerField(choices=RECORD_TYPE_CHOICES)
    content = models.TextField()
    ttl = models.SmallIntegerField()
    priority = models.SmallIntegerField()
    status = models.PositiveSmallIntegerField(choices=RECORD_STATUS_CHOICES)
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)