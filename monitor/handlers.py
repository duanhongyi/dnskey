import logging
import threading

from django.core.signals import request_started, request_finished
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

from domain.models import Record
from domain.signals import query_records
from domain.query import LocalQueryProxy
from .models import Monitor
from .checker import TcpChecker, HttpChecker

monitor_key_ids_template = "monitor_ids_by_record_id:%s"

@receiver(post_save, sender=Record)
def monitor_post_save_handler(instance, **kwargs):
    record_id = instance.pk
    monitors_map = {}
    for monitor in Monitor.objects.filter(record_id=record_id).all():
        monitors_map["monitor:%s" % monitor.pk] = monitor
    cache.set_many(monitors_map)

    monitor_ids = [
        m.pk for m in monitors_map.values()]
    cache.set(monitor_key_ids_template % record_id, monitor_ids)


@receiver(query_records, sender=LocalQueryProxy)
def query_records_handler(records, **kwargs):
    def check_records(records):
        try:
            request_started.send(sender=__name__)
            records_map = {}
            for record in records:
                records_map[record.pk] = record
                record.incr_recent_query_times(1)
            for monitor in _get_monitors(records):
                record = records_map[monitor.record_id]
                if monitor.mtype == 1:  # tcp
                    checker = TcpChecker(record, monitor)
                elif monitor.mtype == 2:
                    checker = HttpChecker(record, monitor)
                thread = threading.Thread(target=checker)
                thread.daemon = True
                thread.start() 
        finally:
            request_finished.send(sender=__name__)

    thread = threading.Thread(target=check_records, args=(records, ))
    thread.daemon = True
    thread.start()


def _get_monitors(records):
    monitors_ids_key = []
    for values in cache.get_many([
        monitor_key_ids_template % record.pk for record in records]).values():
        monitors_ids_key.extend(["monitor:%s" % v for v in values])
    monitors_map = cache.get_many(monitors_ids_key)

    uncached_records = [] 
    for record in records:
        is_matching = False
        for monitor in monitors_map.values():
            if record.pk == monitor.record_id:
                is_matching = True
                break
        if not is_matching: uncached_records.append(record)
    
    uncached_monitors_map, uncached_record_ids_map = {}, {}
    for monitor in Monitor.objects.filter(
            record_id__in=[record.pk for record in uncached_records]).all():
        uncached_monitors_map["monitor:%s" % monitor.pk] = monitor
        key = monitor_key_ids_template % monitor.record_id
        if key not in uncached_record_ids_map:
            uncached_record_ids_map[key] = []
        uncached_record_ids_map[key].append(monitor.pk)
    cache.set_many(uncached_monitors_map)
    cache.set_many(uncached_record_ids_map)
    monitors_map.update(uncached_monitors_map)
    return list(monitors_map.values())