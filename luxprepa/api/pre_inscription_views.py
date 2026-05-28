import random
import jwt
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import (
    User, Eleve, Prof, Admin,
    InscriptionTemporaire
)
from .serializers import envoyer_sms, generer_token_jwt


# ───────────────────────────────────────────
# UTILITAIRES
# ───────────────────────────────────────────

def generer_code_sms():
    return str(random.randint(100000, 999999))


# ───────────────────────────────────────────
# SERIALIZER ÉTAPE 1 — Envoi des données
# ───────────────────────────────────────────

class PreInscriptionSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    telephone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=['eleve', 'prof', 'admin'])

    # Champs spécifiques élève
    date_naissance = serializers.DateField(required=False, allow_null=True)
    tel_parent = serializers.CharField(max_length=20, required=False, allow_blank=True)
    niveau = serializers.ChoiceField(
        choices=['tle','post_bac'],required=False,allow_null=True
    )
    # Champs spécifiques prof
    specialite = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_telephone(self, value):
        # Vérifier que le numéro n'est pas déjà utilisé par un vrai compte
        if User.objects.filter(telephone=value).exists():
            raise serializers.ValidationError("Ce numéro est déjà associé à un compte.")
        return value

    def validate(self, data):
        if data.get('role') == 'prof' and not data.get('specialite'):
            raise serializers.ValidationError({
                "specialite": "La spécialité est obligatoire pour un professeur."
            })
        return data

    def save(self):
        data = self.validated_data
        telephone = data['telephone']

        # Supprimer une éventuelle inscription temporaire existante
        # (si l'utilisateur refait une tentative)
        InscriptionTemporaire.objects.filter(telephone=telephone).delete()

        # Générer le code SMS
        code = generer_code_sms()

        # Créer l'inscription temporaire
        temp = InscriptionTemporaire.objects.create(
            nom=data['nom'],
            prenom=data['prenom'],
            telephone=telephone,
            password_hash=make_password(data['password']),
            role=data['role'],
            date_naissance=data.get('date_naissance'),
            tel_parent=data.get('tel_parent', ''),
            niveau=data.get('niveau'),
            specialite=data.get('specialite', ''),
            code_sms=code,
            code_expire_at=timezone.now() + timedelta(minutes=10),
        )

        # Envoyer le SMS
        message = f"LuxPrepa - Votre code de confirmation est : {code}. Valable 10 minutes."
        envoyer_sms(telephone, message)

        return temp

class ConfirmationSMSSerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, data):
        telephone = data['telephone']
        code = data['code']

        # Récupérer l'inscription temporaire
        try:
            temp = InscriptionTemporaire.objects.get(telephone=telephone)
        except InscriptionTemporaire.DoesNotExist:
            raise serializers.ValidationError({
                "telephone": "Aucune inscription en attente pour ce numéro."
            })

        # Vérifier expiration
        if temp.est_expire():
            temp.delete()
            raise serializers.ValidationError({
                "code": "Le code a expiré. Veuillez recommencer l'inscription."
            })

        # Vérifier nombre de tentatives
        if temp.trop_de_tentatives():
            temp.delete()
            raise serializers.ValidationError({
                "code": "Trop de tentatives incorrectes. Veuillez recommencer l'inscription."
            })

        # Vérifier le code
        if temp.code_sms != code:
            temp.tentatives += 1
            temp.save()
            restantes = 3 - temp.tentatives
            raise serializers.ValidationError({
                "code": f"Code incorrect. {restantes} tentative(s) restante(s)."
            })

        data['temp'] = temp
        return data

    def save(self):
        temp = self.validated_data['temp']

        # Créer le vrai compte selon le rôle
        base_data = {
            "nom": temp.nom,
            "prenom": temp.prenom,
            "telephone": temp.telephone,
            "password": temp.password_hash,
            "role": temp.role,
        }

        if temp.role == 'eleve':
            user = Eleve(
                **base_data,
                date_naissance=temp.date_naissance,
                tel_parent=temp.tel_parent,
            )
        elif temp.role == 'prof':
            user = Prof(
                **base_data,
                specialite=temp.specialite,
            )
        else:
            user = Admin(**base_data)

        user.save_without_hashing()

        # Supprimer l'inscription temporaire
        temp.delete()

        # Générer le token JWT
        token = generer_token_jwt(user)

        return user, token


# ───────────────────────────────────────────
# VUE ÉTAPE 1 — Pré-inscription
# ───────────────────────────────────────────

class PreInscriptionView(APIView):
    def post(self, request):
        serializer = PreInscriptionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        temp = serializer.save()

        return Response(
            {
                "message": f"Un code de confirmation a été envoyé au {temp.telephone}.",
                "telephone": temp.telephone,
                "expire_dans": "10 minutes",
            },
            status=status.HTTP_200_OK
        )

class ConfirmationSMSView(APIView):

    def post(self, request):
        serializer = ConfirmationSMSSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, token = serializer.save()

        return Response(
            {
                "message": "Compte créé avec succès. Bienvenue sur LuxPrepa !",
                "token": token,
                "user": {
                    "id": str(user.id),
                    "nom": user.nom,
                    "prenom": user.prenom,
                    "telephone": user.telephone,
                    "role": user.role,
                }
            },
            status=status.HTTP_201_CREATED
        )

class RenvoyerCodeView(APIView):
    """
    POST /api/auth/renvoyer-code/
    Génère un nouveau code et le renvoie par SMS.

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

        try:
            temp = InscriptionTemporaire.objects.get(telephone=telephone)
        except InscriptionTemporaire.DoesNotExist:
            return Response(
                {"erreur": "Aucune inscription en attente pour ce numéro."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Générer un nouveau code et réinitialiser
        nouveau_code = generer_code_sms()
        temp.code_sms = nouveau_code
        temp.code_expire_at = timezone.now() + timedelta(minutes=10)
        temp.tentatives = 0
        temp.save()

        # Renvoyer le SMS
        message = f"LuxPrepa - Votre nouveau code est : {nouveau_code}. Valable 10 minutes."
        envoyer_sms(telephone, message)

        return Response(
            {
                "message": f"Un nouveau code a été envoyé au {telephone}.",
                "expire_dans": "10 minutes",
            },
            status=status.HTTP_200_OK
        )