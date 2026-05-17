import jwt
import random
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from .models import User, Eleve, Admin, Prof

def generer_code_sms():
    return str(random.randint(100000, 999999))


def detecter_operateur(telephone):
    prefixes_orange = ('69', '655', '656', '657', '658', '659', '650' ,'651', '652', '653', '654')
    prefixes_mtn    = ('67', '68', '650', '651', '652', '653', '654')

    # Vérifier d'abord les préfixes à 3 chiffres (plus précis)
    if telephone.startswith(('655', '656', '657', '658', '659')):
        return 'orange'
    if telephone.startswith(('650', '651', '652', '653', '654')):
        return 'mtn'
    # Puis les préfixes à 2 chiffres
    if telephone.startswith('69'):
        return 'orange'
    if telephone.startswith(('67', '68')):
        return 'mtn'

    return None  # Opérateur inconnu


def envoyer_sms_orange(telephone, message):
    url = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B237{}/requests".format(
        settings.ORANGE_SMS_SENDER_NUMBER
    )
    headers = {
        "Authorization": f"Bearer {settings.ORANGE_SMS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "outboundSMSMessageRequest": {
            "address": f"tel:+237{telephone}",
            "senderAddress": f"tel:+237{settings.ORANGE_SMS_SENDER_NUMBER}",
            "outboundSMSTextMessage": {
                "message": message
            }
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 201
    except Exception:
        return False


def envoyer_sms_mtn(telephone, message):
    url = "https://api.mtn.com/v1/sms/messages"
    headers = {
        "Authorization": f"Bearer {settings.MTN_SMS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "senderAddress": settings.MTN_SMS_SENDER_NUMBER,
        "receiverAddress": [f"+237{telephone}"],
        "message": message,
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in (200, 201)
    except Exception:
        return False


def envoyer_sms(telephone, message):
    operateur = detecter_operateur(telephone)

    if operateur == 'orange':
        return envoyer_sms_orange(telephone, message)
    elif operateur == 'mtn':
        return envoyer_sms_mtn(telephone, message)
    else:
        return envoyer_sms_orange(telephone, message)


def generer_token_jwt(user):
    payload = {
        "user_id": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


# ───────────────────────────────────────────
# INSCRIPTION
# ───────────────────────────────────────────

class InscriptionSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    telephone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=['eleve', 'prof', 'admin'])

    # Champs spécifiques à l'élève (optionnels)
    date_naissance = serializers.DateField(required=False, allow_null=True)
    tel_parent = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Champs spécifiques au prof (optionnel)
    specialite = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_telephone(self, value):
        """Vérifie que le numéro n'est pas déjà utilisé"""
        if User.objects.filter(telephone=value).exists():
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return value

    def validate(self, data):
        """Vérifie les champs obligatoires selon le rôle"""
        role = data.get('role')
        if role == 'prof' and not data.get('specialite'):
            raise serializers.ValidationError({
                "specialite": "La spécialité est obligatoire pour un professeur."
            })
        return data

    def create(self, validated_data):
        role = validated_data.get('role')

        # Champs communs
        base_data = {
            "nom": validated_data["nom"],
            "prenom": validated_data["prenom"],
            "telephone": validated_data["telephone"],
            "password": validated_data["password"],  # hashé automatiquement via save()
            "role": role,
        }

        # Créer selon le rôle
        if role == 'eleve':
            user = Eleve.objects.create(
                **base_data,
                date_naissance=validated_data.get("date_naissance"),
                tel_parent=validated_data.get("tel_parent", ""),
            )
        elif role == 'prof':
            user = Prof.objects.create(
                **base_data,
                specialite=validated_data.get("specialite", ""),
            )
        else:
            user = Admin.objects.create(**base_data)

        # Générer et envoyer le code SMS
        code = generer_code_sms()

        # Stocker le code temporairement dans un champ ou cache
        # Pour l'instant on l'envoie directement par SMS
        message = f"Bienvenue sur LuxPrepa ! Votre code de confirmation est : {code}"
        envoyer_sms(user.telephone, message)

        # Retourner le user et le code (le code sera stocké côté vue)
        return user, code


# ───────────────────────────────────────────
# CONNEXION
# ───────────────────────────────────────────

class ConnexionSerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        telephone = data.get("telephone")
        password = data.get("password")

        # Chercher l'utilisateur par son numéro
        try:
            user = User.objects.get(telephone=telephone)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "telephone": "Aucun compte trouvé avec ce numéro."
            })

        # Vérifier le mot de passe
        if not check_password(password, user.password):
            raise serializers.ValidationError({
                "password": "Mot de passe incorrect."
            })

        # Générer le token JWT
        token = generer_token_jwt(user)

        return {
            "token": token,
            "user": {
                "id": str(user.id),
                "nom": user.nom,
                "prenom": user.prenom,
                "telephone": user.telephone,
                "role": user.role,
            }
        }