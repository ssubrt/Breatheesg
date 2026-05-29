"""Custom DRF permission classes"""
from rest_framework import permissions


class IsInOrganization(permissions.BasePermission):
    """
    Permission to ensure user belongs to the organization
    """
    
    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and request.user.profile is not None
    
    def has_object_permission(self, request, view, obj):
        """Check if object belongs to user's organization"""
        if not hasattr(request.user, 'profile'):
            return False
        
        # Handle different object types
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.profile.organization
        elif hasattr(obj, 'organization_id'):
            return obj.organization_id == request.user.profile.organization_id
        
        return False


class IsAnalystOrHigher(permissions.BasePermission):
    """
    Permission for analyst+ operations (approve, reject, notes)
    """
    
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role in ['ANALYST', 'ADMIN']
    
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'profile'):
            return False
        
        # Must belong to same organization
        if hasattr(obj, 'organization'):
            if obj.organization != request.user.profile.organization:
                return False
        
        # Must have analyst+ role
        return request.user.profile.role in ['ANALYST', 'ADMIN']


class IsAdminOrHigher(permissions.BasePermission):
    """
    Permission for admin operations
    """
    
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        
        return request.user.profile.role == 'ADMIN'
    
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'profile'):
            return False
        
        # Must belong to same organization
        if hasattr(obj, 'organization'):
            if obj.organization != request.user.profile.organization:
                return False
        
        # Must have admin role
        return request.user.profile.role == 'ADMIN'
