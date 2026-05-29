from django.contrib import admin
from .models import Organization, UserProfile, DataSource, RawEmission, AuditLog


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_domain', 'created_at')
    search_fields = ('name', 'email_domain')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'created_at')
    list_filter = ('role', 'organization')
    search_fields = ('user__username', 'user__email')


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('organization', 'source_type', 'filename', 'ingested_at', 'record_count')
    list_filter = ('source_type', 'organization')


@admin.register(RawEmission)
class RawEmissionAdmin(admin.ModelAdmin):
    list_display = ('activity_type', 'activity_value', 'activity_unit', 'scope', 'category', 'status', 'activity_date')
    list_filter = ('status', 'scope', 'category', 'organization')
    search_fields = ('activity_type', 'source_reference_id')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('emission', 'action', 'changed_by', 'timestamp')
    list_filter = ('action',)
    readonly_fields = ('emission', 'action', 'changed_by', 'changes', 'timestamp', 'notes')
