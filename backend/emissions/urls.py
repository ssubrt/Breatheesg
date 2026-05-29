from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet, UserProfileViewSet, DataSourceViewSet,
    RawEmissionViewSet, IngestionViewSet, AnalyticsViewSet
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'users', UserProfileViewSet, basename='userprofile')
router.register(r'data-sources', DataSourceViewSet, basename='datasource')
router.register(r'emissions', RawEmissionViewSet, basename='rawemission')
router.register(r'ingestion', IngestionViewSet, basename='ingestion')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

app_name = 'emissions'

urlpatterns = [
    path('', include(router.urls)),
]
