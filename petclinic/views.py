from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from petclinic.models import Owner, Pet, PetType, Specialty, User, Vet, Visit
from petclinic.serializers import (OwnerSerializer, PetSerializer,
                                   PetTypeSerializer, SpecialtySerializer,
                                   UserSerializer, VetSerializer,
                                   VisitSerializer)
from rest_framework_simplejwt.authentication import JWTAuthentication

from petclinic.metering.collector import record_mcp_access
from petclinic.metering.identity import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    COOKIE_SALT,
)


class UserList(APIView):
    """
    List all users with profile
    """

    def get(self, request, format=None):
        users = User.objects.all()
        serializer_context = { 'request': request }
        serializer = UserSerializer(users, many=True, context=serializer_context)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer_context = { 'request': request }
        serializer = UserSerializer(data=request.data, context=serializer_context)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetail(APIView):
    """
    Retrieve and update users
    """
    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer_context = { 'request': request }
        serializer = UserSerializer(user, context=serializer_context)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer_context = { 'request': request }
        serializer = UserSerializer(user, data=request.data, partial=True, context=serializer_context)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        user = self.get_object(pk)
        user.delete()
        return Response(status.HTTP_204_NO_CONTENT)


class OwnerList(APIView):
    """
    List all owners, or create a new owner
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        owners = Owner.objects.all()
        state = request.query_params.get('state', None)
        if state is not None:
            owners = owners.filter(state=state)
        serializer = OwnerSerializer(owners, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = OwnerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OwnerDetail(APIView):
    """
    Retrive, update or delete a specific owner instance
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_object(self, pk):
        try:
            return Owner.objects.get(pk=pk)
        except Owner.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        owner = self.get_object(pk)
        serializer = OwnerSerializer(owner)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        owner = self.get_object(pk)
        serializer = OwnerSerializer(owner, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        owner = self.get_object(pk)
        owner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class VetList(APIView):
    """
    List all vets or create a new vet
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]   

    def get(self, request, format=None):
        vets = Vet.objects.all()
        state = request.query_params.get('state', None)
        if state is not None:
            vets = vets.filter(state=state)
        serializer = VetSerializer(vets, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = VetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VetDetail(APIView):
    """
    Retrieve, update or delete specific instances of a vet
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]  

    def get_object(self, pk):
        try:
            return Vet.objects.get(pk=pk)
        except Vet.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        vet = self.get_object(pk)
        serializer = VetSerializer(vet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        vet = self.get_object(pk)
        serializer = VetSerializer(vet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        vet = self.get_object(pk)
        vet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)    

class SpecialtyList(APIView):
    """
    List all specialties
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        specialties = Specialty.objects.all()
        serializer = SpecialtySerializer(specialties, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = SpecialtySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SpecialtyDetail(APIView):
    """
    Retrieve, update a speciality (delete blocked)
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_object(self, pk):
        try:
            return Specialty.objects.get(pk=pk)
        except Specialty.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        specialty = self.get_object(pk)
        serializer = SpecialtySerializer(specialty)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        specialty = self.get_object(pk)
        serializer = SpecialtySerializer(specialty, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.erors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        data = { 'message': 'Unsupported operation'}
        return Response(data, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class PetTypeList(APIView):
    """
    List all or create a new pet types
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        pet_types = PetType.objects.all()
        serializer = PetTypeSerializer(pet_types, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = PetTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PetTypeDetail(APIView):
    """
    Retrieve, update a pet type (delete blocked)
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_object(self, pk):
        try:
            return PetType.objects.get(pk=pk)
        except PetType.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        pet_type = self.get_object(pk)
        serializer = PetTypeSerializer(pet_type)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        pet_type = self.get_object(pk)
        serializer = PetTypeSerializer(pet_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        data = { 'message': 'Unsupported operation'}
        return Response(data, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class OwnerPetList(generics.ListCreateAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]    

    def get_queryset(self):
        owner_pk = self.kwargs['owner_pk']
        return self.queryset.filter(owner=owner_pk)

    def pre_save(self, obj):
        obj.owner = self.kwargs['owner_pk']

    def create(self, request, *args, **kwargs):
        owner_id = self.kwargs['owner_pk']
        for pet_data in request.data:
            pet_data['owner'] = owner_id
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)
        pets_created = []
        for pet_data in request.data:
            pet_data['owner'] = Owner.objects.get(pk=owner_id)
            pet_data['pet_type'] = PetType.objects.get(pk=pet_data['pet_type'])
            pet = Pet(**pet_data)
            pet.save()
            pets_created.append(pet.id)
        results = Pet.objects.filter(id__in=pets_created)
        output_serializer = PetSerializer(results, many=True)
        data = output_serializer.data[:]
        return Response(data, status=status.HTTP_201_CREATED)

class PetVisitList(generics.ListCreateAPIView):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]    

    def get_queryset(self):
        pet_pk = self.kwargs['pet_pk']
        return self.queryset.filter(pet=pet_pk)

    def pre_save(self, obj):
        obj.pet = self.kwargs['pet_pk']

    def create(self, request, *args, **kwargs):
        pet_id = self.kwargs['pet_pk']
        for visit_data in request.data:
            visit_data['pet'] = pet_id
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)
        visits_created = []
        for visit_data in request.data:
            visit_data['pet'] = Pet.objects.get(pk=pet_id)
            visit = Visit.objects.create(**visit_data)
            visits_created.append(visit.id)
        results = Visit.objects.filter(id__in=visits_created)
        output_serializer = VisitSerializer(results, many=True)
        data = output_serializer.data[:]
        return Response(data, status=status.HTTP_201_CREATED)

class PetDetail(APIView):
    """
    Retrieval, update or delete a pet
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_object(self, pk):
        try:
            return Pet.objects.get(pk=pk)
        except Pet.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        pet = self.get_object(pk)
        serializer = PetSerializer(pet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        pet = self.get_object(pk)
        serializer = PetSerializer(pet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        pet = self.get_object(pk)
        pet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class VisitDetail(APIView):
    """
    Retrieve, update or delete visit by pk
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
        
    def get_object(self, pk):
        try:
            return Visit.objects.get(pk=pk)
        except Visit.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        visit = self.get_object(pk)
        serializer = VisitSerializer(visit)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        visit = self.get_object(pk)
        serializer = VisitSerializer(visit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        visit = self.get_object(pk)
        visit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# MCP event boundary for the HS_MCP_MONTLY_USER_COUNT metric.
#
# This is the *only* instrumented endpoint. Generic DRF CRUD views above and
# any health/static endpoints are intentionally NOT instrumented so that
# unrelated HTTP traffic (health checks, asset fetches, admin/CRUD traffic)
# is excluded from the metric population (per the measurement contract).
#
# The branding term 'Product Standard MCP server' is interpreted as
# provenance for this service; this dedicated DRF endpoint is designated
# as the served MCP interaction boundary.
# ---------------------------------------------------------------------------
class MCPInteractionView(APIView):
    """Designated MCP event boundary.

    POST /mcp/interaction/ represents a served MCP interaction
    attributable to a user. Metering is recorded ONLY after the
    handler has completed successfully, just before the 200 response
    is returned, so failed/rejected interactions do not count.
    """

    # Permissive so anonymous callers can be measured via a
    # server-issued pseudonymous cookie; if request.user is
    # authenticated, that principal is used instead.
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, format=None):
        # Perform the MCP-equivalent work first; any exception raised
        # here aborts the request before metering is recorded, so
        # failed interactions are excluded from the metric.
        result = self.handle_mcp(request)

        # Success boundary: handler completed; record then respond.
        cookie_to_set = record_mcp_access(request)

        response = Response(result, status=status.HTTP_200_OK)
        if cookie_to_set:
            response.set_signed_cookie(
                COOKIE_NAME,
                cookie_to_set,
                salt=COOKIE_SALT,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                secure=True,
                samesite='Lax',
            )
        return response

    def handle_mcp(self, request):
        """Perform the MCP interaction.

        Kept as a hook so the metering wiring is independent of the
        concrete MCP work. Returns a serializable payload echoed back
        to the caller.
        """
        payload = request.data if hasattr(request, 'data') else {}
        return {'status': 'ok', 'echo': payload}
