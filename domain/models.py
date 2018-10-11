import uuid
from django.db import models
from django.contrib.auth.models import User

class Domain(models.Model):
    DOMAIN_DTYPE_CHOICES = (
        (1, "stub"),
        (1, "primary"),
        (1, "secondary"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operators = models.ManyToManyField(User, related_name="domain_operators")
    dtype = models.PositiveSmallIntegerField(choices=DOMAIN_DTYPE_CHOICES)
    name = models.CharField(unique=True, max_length=255, db_index=True)
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Region(models.Model):
    state = models.CharField(max_length=128)
    province = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    zone = models.CharField(max_length=128)
    start_address = models.DecimalField(db_index=True, max_digits=40, decimal_places=0)
    end_address = models.DecimalField(db_index=True, max_digits=40, decimal_places=0)
    description = models.TextField(blank=True)


class Record(models.Model):
    RECORD_RTYPE_CHOICES = (
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

    RECORD_RCLASS_CHOICES = (
        (1, 'IN'), 
        (2, 'CS'),
        (3, 'CH'),
        (4, 'Hesiod'),
        (254, 'None'),
        (255, '*'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    region_name = models.CharField(max_length=32, db_index=True)
    subdomain = models.CharField(max_length=255, db_index=True)
    full_subdomain = models.CharField(max_length=255, db_index=True)
    rtype = models.PositiveSmallIntegerField(choices=RECORD_RTYPE_CHOICES)
    rclass = models.PositiveSmallIntegerField(choices=RECORD_RCLASS_CHOICES)
    content = models.TextField()
    ttl = models.SmallIntegerField()
    status = models.PositiveSmallIntegerField(choices=RECORD_STATUS_CHOICES)
    created_time=models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)