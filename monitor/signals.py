from django.db.models.signals import port_save
from django.dispatch import receiver
from django.core.cache import cache

from .models import Monitor

@receiver(post_save, sender=Monitor)
def monitor_post_save_handler(instance, **kwargs):
    cache.set("monitor:%s" % instance.pk, instance)