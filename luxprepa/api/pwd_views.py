import jwt
import random
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, InscriptionTemporaire
from .serializers import envoyer_sms

def generer_code_sms():
    return str(random.randint(100000, 999999))

def get_user_from_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return User.objects.get(id=payload['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return None

def reponse_non_autorise():
    return Response(
        {"erreur": "Token invalide ou expiré."},
        status=status.HTTP_401_UNAUTHORIZED
    )

class ChangerMotDePasseSerializer(serializers.Serializer):
    ancien_password = serializers.CharField(write_only=True)
    nouveau_password = serializers.CharField(write_only=True, min_length=6)
    confirmer_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        # Vérifier que nouveau et confirmation correspondent
        if data['nouveau_password'] != data['confirmer_password']:
            raise serializers.ValidationError({
                "confirmer_password": "Les deux mots de passe ne correspondent pas."
            })

        # Vérifier que le nouveau est différent de l'ancien
        if data['ancien_password'] == data['nouveau_password']:
            raise serializers.ValidationError({
                "nouveau_password": "Le nouveau mot de passe doit être différent de l'ancien."
            })

        return data

class ChangerMotDePasseView(APIView):
    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        serializer = ChangerMotDePasseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Vérifier l'ancien mot de passe
        if not check_password(data['ancien_password'], user.password):
            return Response(
                {"erreur": "Ancien mot de passe incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mettre à jour le mot de passe
        user.password = make_password(data['nouveau_password'])
        user.save_without_hashing()

        return Response(
            {"message": "Mot de passe modifié avec succès."},
            status=status.HTTP_200_OK
        )

class MotDePasseOublieView(APIView):
    """
    POST /api/auth/mot-de-passe-oublie/
    Accès : Public

    Corps :
    {
        "telephone": "690000000"
    }
    """

    def post(self, request):
        telephone = request.data.get('telephone')

        if not telephone:
            return Response(
                {"erreur": "Le numéro de téléphone est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le compte existe
        try:
            user = User.objects.get(telephone=telephone)
        except User.DoesNotExist:
            return Response(
                {"erreur": "Aucun compte trouvé avec ce numéro."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Supprimer un éventuel code existant
        InscriptionTemporaire.objects.filter(telephone=telephone).delete()

        # Générer le code
        code = generer_code_sms()

        # Stocker dans InscriptionTemporaire en mode "reset"
        # On met juste le téléphone et le code, le reste est vide
        InscriptionTemporaire.objects.create(
            nom=user.nom,
            prenom=user.prenom,
            telephone=telephone,
            password_hash='reset',  # marqueur pour distinguer du flow inscription
            role=user.role,
            code_sms=code,
            code_expire_at=timezone.now() + timedelta(minutes=10),
        )

        # Envoyer le SMS
        message = f"LuxPrepa - Code de réinitialisation : {code}. Valable 10 minutes."
        envoyer_sms(telephone, message)

        return Response(
            {
                "message": f"Un code de réinitialisation a été envoyé au {telephone}.",
                "telephone": telephone,
                "expire_dans": "10 minutes",
            },
            status=status.HTTP_200_OK
        )

class VerifierCodeResetView(APIView):
    """
    POST /api/auth/verifier-code-reset/
    Accès : Public

    Corps :
    {
        "telephone": "690000000",
        "code": "123456"
    }
    """

    def post(self, request):
        telephone = request.data.get('telephone')
        code = request.data.get('code')

        if not telephone or not code:
            return Response(
                {"erreur": "Numéro et code sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            temp = InscriptionTemporaire.objects.get(telephone=telephone)
        except InscriptionTemporaire.DoesNotExist:
            return Response(
                {"erreur": "Aucune demande de réinitialisation pour ce numéro."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier expiration
        if temp.est_expire():
            temp.delete()
            return Response(
                {"erreur": "Le code a expiré. Veuillez recommencer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier tentatives
        if temp.trop_de_tentatives():
            temp.delete()
            return Response(
                {"erreur": "Trop de tentatives. Veuillez recommencer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier le code
        if temp.code_sms != code:
            temp.tentatives += 1
            temp.save()
            restantes = 3 - temp.tentatives
            return Response(
                {"erreur": f"Code incorrect. {restantes} tentative(s) restante(s)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Code valide → retourner un token temporaire de reset
        # Ce token sera utilisé à l'étape 3 pour changer le mot de passe
        import uuid
        reset_token = str(uuid.uuid4())
        temp.password_hash = f"reset_token:{reset_token}"
        temp.save()

        return Response(
            {
                "message": "Code vérifié avec succès.",
                "reset_token": reset_token,
                "telephone": telephone,
            },
            status=status.HTTP_200_OK
        )

class NouveauMotDePasseSerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=20)
    reset_token = serializers.CharField()
    nouveau_password = serializers.CharField(write_only=True, min_length=6)
    confirmer_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data['nouveau_password'] != data['confirmer_password']:
            raise serializers.ValidationError({
                "confirmer_password": "Les deux mots de passe ne correspondent pas."
            })
        return data

class NouveauMotDePasseView(APIView):

    def post(self, request):
        serializer = NouveauMotDePasseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        telephone = data['telephone']
        reset_token = data['reset_token']

        # Récupérer la demande temporaire
        try:
            temp = InscriptionTemporaire.objects.get(telephone=telephone)
        except InscriptionTemporaire.DoesNotExist:
            return Response(
                {"erreur": "Demande de réinitialisation introuvable ou expirée."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier le reset_token
        token_attendu = f"reset_token:{reset_token}"
        if temp.password_hash != token_attendu:
            return Response(
                {"erreur": "Token de réinitialisation invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier expiration
        if temp.est_expire():
            temp.delete()
            return Response(
                {"erreur": "La session a expiré. Veuillez recommencer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mettre à jour le mot de passe
        try:
            user = User.objects.get(telephone=telephone)
        except User.DoesNotExist:
            return Response(
                {"erreur": "Utilisateur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        user.password = make_password(data['nouveau_password'])
        user.save_without_hashing()

        # Supprimer la demande temporaire
        temp.delete()

        return Response(
            {"message": "Mot de passe réinitialisé avec succès. Vous pouvez vous connecter."},
            status=status.HTTP_200_OK
        )