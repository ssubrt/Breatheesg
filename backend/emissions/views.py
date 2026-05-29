from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, timedelta
import json

from .models import Organization, UserProfile, DataSource, RawEmission, AuditLog
from .serializers import (
    OrganizationSerializer, UserProfileSerializer, DataSourceSerializer,
    RawEmissionSerializer, RawEmissionListSerializer, RawEmissionDetailSerializer,
    IngestionResponseSerializer, AuditLogSerializer, AnalyticsSerializer
)
from .permissions import IsInOrganization, IsAnalystOrHigher
from .processors.sap import SAPProcessor
from .processors.utility import UtilityProcessor
from .processors.travel import TravelProcessor


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD operations for organizations"""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    
    def get_queryset(self):
        # Only return org if user belongs to it
        if hasattr(self.request.user, 'profile'):
            return Organization.objects.filter(id=self.request.user.profile.organization_id)
        return Organization.objects.none()


class UserProfileViewSet(viewsets.ModelViewSet):
    """User profile management"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile'):
            return UserProfile.objects.filter(organization=self.request.user.profile.organization)
        return UserProfile.objects.none()


class DataSourceViewSet(viewsets.ModelViewSet):
    """Ingestion data source tracking"""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'profile'):
            return DataSource.objects.filter(organization=self.request.user.profile.organization)
        return DataSource.objects.none()


class RawEmissionViewSet(viewsets.ModelViewSet):
    """Emissions records - list, retrieve, approve, reject"""
    queryset = RawEmission.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'profile'):
            return RawEmission.objects.none()
        
        qs = RawEmission.objects.filter(
            organization=self.request.user.profile.organization
        ).select_related('data_source', 'reviewed_by')
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__in=status_param.split(','))
        
        # Filter by scope
        scope_param = self.request.query_params.get('scope')
        if scope_param:
            qs = qs.filter(scope__in=scope_param.split(','))
        
        # Filter by category
        category_param = self.request.query_params.get('category')
        if category_param:
            qs = qs.filter(category__in=category_param.split(','))
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(activity_date__gte=date_from)
        if date_to:
            qs = qs.filter(activity_date__lte=date_to)
        
        # Filter by has issues
        has_issues = self.request.query_params.get('has_issues')
        if has_issues == 'true':
            qs = qs.exclude(validation_issues=[])
        
        return qs.order_by('-activity_date')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RawEmissionDetailSerializer
        elif self.action == 'list':
            return RawEmissionListSerializer
        return RawEmissionSerializer
    
    @action(detail=True, methods=['POST'], permission_classes=[permissions.IsAuthenticated, IsAnalystOrHigher])
    def approve(self, request, pk=None):
        """Approve an emissions record"""
        emission = self.get_object()
        
        if emission.status == 'APPROVED':
            return Response({'error': 'Already approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        emission.status = 'APPROVED'
        emission.reviewed_by = request.user
        emission.reviewed_at = datetime.now()
        emission.save()
        
        # Create audit log
        AuditLog.objects.create(
            emission=emission,
            action='APPROVED',
            changed_by=request.user,
            notes=request.data.get('notes', '')
        )
        
        return Response(RawEmissionDetailSerializer(emission).data)
    
    @action(detail=True, methods=['POST'], permission_classes=[permissions.IsAuthenticated, IsAnalystOrHigher])
    def reject(self, request, pk=None):
        """Reject an emissions record"""
        emission = self.get_object()
        
        if emission.status == 'APPROVED':
            return Response({'error': 'Cannot reject approved record'}, status=status.HTTP_400_BAD_REQUEST)
        
        rejection_reason = request.data.get('reason', '')
        if not rejection_reason:
            return Response({'error': 'Rejection reason required'}, status=status.HTTP_400_BAD_REQUEST)
        
        emission.status = 'REJECTED'
        emission.reviewed_by = request.user
        emission.reviewed_at = datetime.now()
        emission.rejection_reason = rejection_reason
        emission.save()
        
        # Create audit log
        AuditLog.objects.create(
            emission=emission,
            action='REJECTED',
            changed_by=request.user,
            notes=rejection_reason
        )
        
        return Response(RawEmissionDetailSerializer(emission).data)
    
    @action(detail=True, methods=['PATCH'], permission_classes=[permissions.IsAuthenticated, IsAnalystOrHigher])
    def update_notes(self, request, pk=None):
        """Add or update analyst notes"""
        emission = self.get_object()
        
        notes = request.data.get('notes', '')
        old_notes = emission.analyst_notes
        emission.analyst_notes = notes
        emission.save()
        
        # Create audit log
        AuditLog.objects.create(
            emission=emission,
            action='NOTES_ADDED',
            changed_by=request.user,
            changes={'analyst_notes': {'old': old_notes, 'new': notes}},
            notes=notes
        )
        
        return Response(RawEmissionDetailSerializer(emission).data)


class IngestionViewSet(viewsets.ViewSet):
    """Data ingestion endpoints for SAP, Utility, Travel"""
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @action(detail=False, methods=['POST'], url_path='sap')
    def ingest_sap(self, request):
        """Ingest SAP fuel and procurement CSV"""
        return self._process_ingestion(request, SAPProcessor(), 'SAP')
    
    @action(detail=False, methods=['POST'], url_path='utility')
    def ingest_utility(self, request):
        """Ingest utility meter CSV"""
        return self._process_ingestion(request, UtilityProcessor(), 'UTILITY')
    
    @action(detail=False, methods=['POST'], url_path='travel')
    def ingest_travel(self, request):
        """Ingest travel expense JSON"""
        return self._process_ingestion(request, TravelProcessor(), 'TRAVEL')
    
    def _process_ingestion(self, request, processor, source_type):
        """Common ingestion processing logic"""
        
        # Get organization from user profile
        if not hasattr(request.user, 'profile'):
            return Response({'error': 'User has no organization'}, status=status.HTTP_400_BAD_REQUEST)
        
        organization = request.user.profile.organization
        
        # Get file content
        if 'file' in request.FILES:
            file_content = request.FILES['file'].read().decode('utf-8')
            filename = request.FILES['file'].name
        elif 'content' in request.data:
            file_content = request.data['content']
            filename = 'pasted_data'
        else:
            return Response({'error': 'No file or content provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process data
        try:
            created_records, errors, warnings = processor.process(file_content, organization.id, request.user)
        except Exception as e:
            return Response(
                {'error': f'Processing failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save data source and emissions
        data_source = DataSource.objects.create(
            organization=organization,
            source_type=source_type,
            filename=filename,
            ingested_by=request.user,
            record_count=len(created_records),
        )
        
        # Save all records
        for emission in created_records:
            emission.organization = organization
            emission.data_source = data_source
            emission.save()
            
            # Create initial audit log
            AuditLog.objects.create(
                emission=emission,
                action='CREATED',
                changed_by=request.user,
            )
        
        # Build response
        response_data = {
            'status': 'success' if not errors else 'partial_success',
            'data_source_id': str(data_source.id),
            'ingested_count': len(created_records),
            'errors': errors,
            'warnings': warnings,
            'created_records': RawEmissionListSerializer(created_records, many=True).data,
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class AnalyticsViewSet(viewsets.ViewSet):
    """Analytics and summary endpoints"""
    permission_classes = [permissions.IsAuthenticated, IsInOrganization]
    
    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """Get emissions summary by scope and category"""
        
        if not hasattr(request.user, 'profile'):
            return Response({'error': 'User has no organization'}, status=status.HTTP_400_BAD_REQUEST)
        
        organization = request.user.profile.organization
        
        # Get filters from query params
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        qs = RawEmission.objects.filter(
            organization=organization,
            status__in=['REVIEWED', 'APPROVED']
        )
        
        if date_from:
            qs = qs.filter(activity_date__gte=date_from)
        if date_to:
            qs = qs.filter(activity_date__lte=date_to)
        
        # Calculate totals by scope
        scope_totals = {}
        for scope in ['SCOPE_1', 'SCOPE_2', 'SCOPE_3']:
            total = qs.filter(scope=scope).aggregate(
                total=Sum('calculated_emissions_kg_co2e')
            )['total'] or Decimal('0')
            scope_totals[scope] = str(total)
        
        # Calculate totals by category
        category_totals = {}
        for emission in qs.values('category').annotate(
            total=Sum('calculated_emissions_kg_co2e')
        ):
            category_totals[emission['category']] = str(emission['total'])
        
        # Status breakdown
        status_breakdown = {}
        for status_val in ['NEW', 'REVIEWED', 'APPROVED', 'REJECTED']:
            count = RawEmission.objects.filter(
                organization=organization,
                status=status_val
            ).count()
            status_breakdown[status_val] = count
        
        # Records with issues
        records_with_issues = RawEmission.objects.filter(
            organization=organization
        ).exclude(validation_issues=[]).count()
        
        # Grand total
        total_emissions = qs.aggregate(total=Sum('calculated_emissions_kg_co2e'))['total'] or Decimal('0')
        
        response_data = {
            'total_emissions_kg_co2e': str(total_emissions),
            'scope_1': scope_totals.get('SCOPE_1', '0'),
            'scope_2': scope_totals.get('SCOPE_2', '0'),
            'scope_3': scope_totals.get('SCOPE_3', '0'),
            'by_category': category_totals,
            'by_status': status_breakdown,
            'records_with_issues': records_with_issues,
        }
        
        return Response(response_data)

