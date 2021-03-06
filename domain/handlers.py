from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

from .models import Record

@receiver(post_save, sender=Record)
def record_post_save_handler(instance, **kwargs):
    cache.set("record:%s" % instance.pk, instance)