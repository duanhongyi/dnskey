from django.contrib import admin
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Domain, Region, Record
from monitor.admin import MonitorInline

# Register your models here.

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'dtype', 'created_time')
    search_fields = ('name', 'description')
    autocomplete_fields = ('operators', )
    exclude = ('user',)
    readonly_fields = []

    def get_queryset(self, request):
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.name.endswith('.'):
            obj.name = '%s.' % obj.name
        obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('state', 'province', 'city', 'zone')
    search_fields = ('state', 'province', 'city', 'zone', 'description')


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = (MonitorInline, )
    list_display = (
        'full_subdomain', 'region_name', 'rtype', 'content', 'status')
    search_fields = ('name', 'content', 'description')
    readonly_fields = ('full_subdomain', )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain":
            q = Q(user=request.user) | Q(operators=request.user)
            kwargs["queryset"] = Domain.objects.filter(q)
        return super(RecordAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def get_queryset(self, request):
        q = Q(domain__user=request.user)
        q |= Q(domain__operators=request.user)
        return super().get_queryset(request).filter(q)
    
    def save_model(self, request, obj, form, change):
        if obj.subdomain == '@':
            obj.full_subdomain = obj.domain.name
        else:
            obj.full_subdomain = '%s.%s' % (obj.subdomain, obj.domain.name)
        super().save_model(request, obj, form, change)