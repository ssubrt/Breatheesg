from django.db import models
from django.contrib.auth.models import User
import uuid

# Constants
SCOPE_CHOICES = [
    ('SCOPE_1', 'Scope 1 - Direct Emissions'),
    ('SCOPE_2', 'Scope 2 - Indirect Energy'),
    ('SCOPE_3', 'Scope 3 - Other Indirect'),
]

EMISSION_CATEGORY_CHOICES = [
    ('FUEL', 'Fuel Combustion'),
    ('ELECTRICITY', 'Electricity'),
    ('FLIGHTS', 'Flight Travel'),
    ('HOTELS', 'Hotel Stays'),
    ('GROUND_TRANSPORT', 'Ground Transport'),
    ('OTHER', 'Other'),
]

DATA_SOURCE_CHOICES = [
    ('SAP', 'SAP Procurement'),
    ('UTILITY', 'Utility Meters'),
    ('TRAVEL', 'Corporate Travel'),
]

STATUS_CHOICES = [
    ('NEW', 'New - Awaiting Review'),
    ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
]

ROLE_CHOICES = [
    ('ADMIN', 'Administrator'),
    ('ANALYST', 'Analyst'),
    ('VIEWER', 'Viewer'),
]


class Organization(models.Model):
    """Multi-tenant organization container"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email_domain = models.CharField(max_length=255, unique=True, help_text="e.g., company.com")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended user profile with organization and role"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'organization')

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class DataSource(models.Model):
    """Tracks source of ingested data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES)
    filename = models.CharField(max_length=255, blank=True, null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    ingested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    record_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-ingested_at']
        indexes = [
            models.Index(fields=['organization', '-ingested_at']),
        ]

    def __str__(self):
        return f"{self.source_type} - {self.filename} ({self.ingested_at})"


class RawEmission(models.Model):
    """Normalized emissions record from any source"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True)
    source_reference_id = models.CharField(
        max_length=255, 
        help_text="Original row ID from source data"
    )
    
    # Activity data
    activity_date = models.DateField()
    activity_type = models.CharField(max_length=50, help_text="FUEL, kWh, FLIGHT_KM, etc.")
    activity_value = models.DecimalField(max_digits=15, decimal_places=4)
    activity_unit = models.CharField(max_length=50, help_text="L, kg, kWh, km, nights, etc.")
    
    # Classification
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=30, choices=EMISSION_CATEGORY_CHOICES)
    
    # Emission calculation
    emission_factor = models.DecimalField(
        max_digits=15, 
        decimal_places=6,
        help_text="CO2e factor used (kg CO2e per unit)"
    )
    calculated_emissions_kg_co2e = models.DecimalField(max_digits=15, decimal_places=4)
    
    # Review status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_emissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    analyst_notes = models.TextField(blank=True)
    
    # Validation flags
    validation_issues = models.JSONField(default=list, blank=True, help_text="Array of validation issue strings")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', '-activity_date']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['data_source']),
        ]

    def __str__(self):
        return f"{self.activity_type} - {self.activity_value} {self.activity_unit} ({self.activity_date})"


class AuditLog(models.Model):
    """Immutable log of all changes to emissions records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission = models.ForeignKey(RawEmission, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(
        max_length=50, 
        choices=[
            ('CREATED', 'Created'),
            ('UPDATED', 'Updated'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('NOTES_ADDED', 'Notes Added'),
        ]
    )
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changes = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Dict of field changes: {field: {old_value, new_value}}"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['emission', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.emission.id} - {self.action} ({self.timestamp})"
