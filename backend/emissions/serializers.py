from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Organization, UserProfile, DataSource, RawEmission, AuditLog,
    SCOPE_CHOICES, EMISSION_CATEGORY_CHOICES, DATA_SOURCE_CHOICES, STATUS_CHOICES
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'organization', 'organization_name', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'email_domain', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DataSourceSerializer(serializers.ModelSerializer):
    ingested_by_name = serializers.CharField(source='ingested_by.get_full_name', read_only=True)

    class Meta:
        model = DataSource
        fields = [
            'id', 'organization', 'source_type', 'filename', 
            'ingested_at', 'ingested_by', 'ingested_by_name', 'record_count', 'notes'
        ]
        read_only_fields = ['id', 'ingested_at', 'ingested_by']


class AuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'emission', 'action', 'changed_by', 'changed_by_name', 'changes', 'timestamp', 'notes']
        read_only_fields = ['id', 'timestamp']


class RawEmissionSerializer(serializers.ModelSerializer):
    data_source_filename = serializers.CharField(source='data_source.filename', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    audit_logs = AuditLogSerializer(many=True, read_only=True)

    class Meta:
        model = RawEmission
        fields = [
            'id', 'organization', 'data_source', 'data_source_filename',
            'source_reference_id', 'activity_date', 'activity_type',
            'activity_value', 'activity_unit', 'scope', 'category',
            'emission_factor', 'calculated_emissions_kg_co2e', 'status',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'rejection_reason',
            'analyst_notes', 'validation_issues', 'created_at', 'updated_at', 'audit_logs'
        ]
        read_only_fields = [
            'id', 'organization', 'data_source', 'calculated_emissions_kg_co2e',
            'created_at', 'updated_at', 'audit_logs'
        ]


class RawEmissionDetailSerializer(RawEmissionSerializer):
    """Extended serializer for detail views with full audit log"""
    pass


class RawEmissionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    data_source_filename = serializers.CharField(source='data_source.filename', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)

    class Meta:
        model = RawEmission
        fields = [
            'id', 'source_reference_id', 'activity_date', 'activity_type',
            'activity_value', 'activity_unit', 'scope', 'category',
            'calculated_emissions_kg_co2e', 'status', 'data_source_filename',
            'reviewed_by_name', 'validation_issues', 'created_at'
        ]
        read_only_fields = fields


class IngestionResponseSerializer(serializers.Serializer):
    """Response format for ingestion endpoints"""
    status = serializers.CharField()
    data_source_id = serializers.UUIDField()
    ingested_count = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    created_records = RawEmissionListSerializer(many=True)


class AnalyticsSerializer(serializers.Serializer):
    """Analytics summary data"""
    total_emissions_kg_co2e = serializers.DecimalField(max_digits=15, decimal_places=4)
    scope_1 = serializers.DecimalField(max_digits=15, decimal_places=4)
    scope_2 = serializers.DecimalField(max_digits=15, decimal_places=4)
    scope_3 = serializers.DecimalField(max_digits=15, decimal_places=4)
    by_category = serializers.DictField()
    by_status = serializers.DictField()
    records_with_issues = serializers.IntegerField()
