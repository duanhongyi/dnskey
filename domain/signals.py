import django.dispatch


query_records = django.dispatch.Signal(providing_args=["records", ])