from django.shortcuts import render
import jwt
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, ConnexionSerializer,EleveSerializer
from .models import User,Eleve,Prof
from .permissions import IsAdminRole
from rest_framework.parsers import MultiPartParser,FormParser
from .concours_views import get_user_from_token,reponse_non_autorise,reponse_admin_requis
def verifier_token(request):
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

class InscriptionView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, code = serializer.save()

        return Response(
            {
                "message": f"Inscription réussie. {user.prenom} {user.nom}",
            },
            status=status.HTTP_201_CREATED
        )

class ConnexionView(APIView):
   
    def post(self, request):
        serializer = ConnexionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # validated_data contient token + infos user
        data = serializer.validated_data

        return Response(
            {
                "message": "Connexion réussie.",
                "token": data["token"],
                "user": data["user"],
            },
            status=status.HTTP_200_OK
        )

class ProfilView(APIView):
    def get(self, request):
        payload = verifier_token(request)

        if payload is None:
            return Response(
                {"erreur": "Token invalide ou expiré. Veuillez vous reconnecter."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            return Response(
                {"erreur": "Utilisateur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.role == 'eleve':
            eleve = Eleve.objects.get(id=user.id)
            return Response(
                {
                    "id": str(eleve.id),
                    "nom": eleve.nom,
                    "prenom": eleve.prenom,
                    "telephone": eleve.telephone,
                    "created_at": eleve.created_at,
                    "date_naissance": eleve.date_naissance,
                    "tel_parent": eleve.tel_parent,
                    "niveau":eleve.niveau,
                    "role":user.role
                }
            )
        
        if user.role == 'prof':
            prof = Prof.objects.get(id=user.id)
            return Response(
                {
                    "id": str(prof.id),
                    "nom": prof.nom,
                    "prenom": prof.prenom,
                    "telephone": prof.telephone,
                    "created_at": prof.created_at,
                    "specialite": prof.specialite,
                    "role":user.role
                }
            )

        return Response(
            {
                "id": str(user.id),
                "nom": user.nom,
                "prenom": user.prenom,
                "telephone": user.telephone,
                "role": user.role,
                "created_at": user.created_at,
            },
            status=status.HTTP_200_OK
        )

class DeconnexionView(APIView):
    def post(self, request):
        payload = verifier_token(request)

        if payload is None:
            return Response(
                {"erreur": "Token invalide ou déjà expiré."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {"message": "Déconnexion réussie."},
            status=status.HTTP_200_OK
        )

class EleveListView(APIView):
    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role not in ('admin', 'prof'):
            return reponse_admin_requis()

        eleves = Eleve.objects.all().order_by('nom')
        serializer = EleveSerializer(eleves, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)