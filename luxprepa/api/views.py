from django.shortcuts import render
import jwt
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, ConnexionSerializer
from .models import User


# ───────────────────────────────────────────
# UTILITAIRE : Décoder le token JWT
# ───────────────────────────────────────────

def verifier_token(request):
    """
    Extrait et vérifie le token JWT depuis le header Authorization.
    Retourne le payload si valide, None sinon.
    """
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


# ───────────────────────────────────────────
# INSCRIPTION
# ───────────────────────────────────────────

class InscriptionView(APIView):
    """
    POST /api/auth/inscription/
    Corps attendu :
    {
        "nom": "Kamga",
        "prenom": "Brayann",
        "telephone": "690000000",
        "password": "monpassword",
        "role": "eleve",
        "date_naissance": "2000-01-01",  # si eleve
        "tel_parent": "670000000",        # si eleve (optionnel)
        "specialite": "Mathématiques"     # si prof
    }
    """

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # create() retourne (user, code)
        user, code = serializer.save()

        return Response(
            {
                "message": "Inscription réussie.",
                "user_id": str(user.id),
            },
            status=status.HTTP_201_CREATED
        )

class ConnexionView(APIView):
    """
    POST /api/auth/connexion/
    Corps attendu :
    {
        "telephone": "690000000",
        "password": "monpassword"
    }
    """

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


# ───────────────────────────────────────────
# PROFIL (route protégée par JWT)
# ───────────────────────────────────────────

class ProfilView(APIView):
    """
    GET /api/auth/profil/
    Header requis : Authorization: Bearer <token>
    """

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


# ───────────────────────────────────────────
# DÉCONNEXION
# ───────────────────────────────────────────

class DeconnexionView(APIView):
    """
    POST /api/auth/deconnexion/
    Côté backend JWT, la déconnexion est gérée côté frontend
    (suppression du token en localStorage).
    Cette vue sert juste à confirmer la déconnexion.
    """

    def post(self, request):
        payload = verifier_token(request)

        if payload is None:
            return Response(
                {"erreur": "Token invalide ou déjà expiré."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {"message": "Déconnexion réussie. Supprimez le token côté client."},
            status=status.HTTP_200_OK
        )