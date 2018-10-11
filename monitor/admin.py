from django.contrib import admin

from .models import Monitor
# Register your models here.

class MonitorInline(admin.StackedInline):
    model = Monitor
    extra = 0