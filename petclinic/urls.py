from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from petclinic import views

urlpatterns = [
    path('users/', views.UserList.as_view(), name='user-list'),
    path('users/<int:pk>', views.UserDetail.as_view(), name='user-detail'),
    path('owners/', views.OwnerList.as_view(), name='owner-list'),
    path('owners/<int:pk>', views.OwnerDetail.as_view(), name='owner-detail'),
    path('vets/', views.VetList.as_view(), name='vet-list'),
    path('vets/<int:pk>', views.VetDetail.as_view(), name='vet-detail'),
    path('specialties/', views.SpecialtyList.as_view(), name='specialty-list'),
    path('specialties/<int:pk>', views.SpecialtyDetail.as_view(), name='specialty-detail'),
    path('pet_types/', views.PetTypeList.as_view(), name='pet-type-list'),
    path('pet_types/<int:pk>', views.PetTypeDetail.as_view(), name='pet-type-detail'),
    path('pets/<int:pk>', views.PetDetail.as_view(), name='pet-detail'),
    path('visits/<int:pk>', views.VisitDetail.as_view(), name='visit-detail'),
    path('owners/<int:owner_pk>/pets', views.OwnerPetList.as_view(), name='owner-pet-list'),
    path('pets/<int:pet_pk>/visits', views.PetVisitList.as_view(), name='pet-visit-list'),
    # Dedicated MCP event boundary for HS_MCP_MONTLY_USER_COUNT metering.
    path('mcp/interaction/', views.MCPInteractionView.as_view(), name='mcp-interaction'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
