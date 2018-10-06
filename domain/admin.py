from django.contrib import admin
from django.contrib.auth.models import User
from .models import Domain, Region, Record
from monitor.admin import MonitorInline

# Register your models here.

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'dtype', 'created_time')
    search_fields = ('name', 'description')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user" and not request.user.is_superuser:
            kwargs["queryset"] = User.objects.filter(username=request.user.username)
        return super(DomainAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.name.endswith('.'):
            obj.name = '%s.' % obj.name
        super().save_model(request, obj, form, change)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('state', 'province', 'city', 'zone')
    search_fields = ('state', 'province', 'city', 'zone', 'description')


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = (MonitorInline, )
    list_display = ('full_subdomain', 'region_name', 'rtype', 'content')
    search_fields = ('name', 'content', 'description')
    readonly_fields = ('full_subdomain', )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain" and not request.user.is_superuser:
            kwargs["queryset"] = Domain.objects.filter(user=request.user)
        return super(RecordAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(domain__user=request.user)
    
    def save_model(self, request, obj, form, change):
        obj.full_subdomain = '%s.%s' % (obj.subdomain, obj.domain.name)
        super().save_model(request, obj, form, change)