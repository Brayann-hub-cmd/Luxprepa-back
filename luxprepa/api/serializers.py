import jwt
import random
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from .models import User, Eleve, Admin, Prof, Concours, Matiere, MatiereConcours,Session, Inscription, Paiement, Eleve, Note,Annonce
from django.db.models import Sum
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

    #Vu que les api sms orange et mtn sont payantes on test en mode dev d'abord
    if settings.SMS_MODE == 'dev':
        print("\n"+'='*40)
        print(f"SMS DEV - Destinataire : {telephone}")
        print(f" Code confirmation: {message}")
        print("="*40+"\n")
        return True

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

class RegisterSerializer(serializers.Serializer):
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

# ───────────────────────────────────────────
# MATIERE
# ───────────────────────────────────────────

class MatiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matiere
        fields = ['id', 'nom', 'description']


# ───────────────────────────────────────────
# MATIERE CONCOURS (avec coefficient)
# ───────────────────────────────────────────

class MatiereConcourSerializer(serializers.ModelSerializer):
    matiere = MatiereSerializer(read_only=True)
    matiere_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = MatiereConcours
        fields = ['id', 'matiere', 'matiere_id', 'coefficient']


# ───────────────────────────────────────────
# CONCOURS - LECTURE
# ───────────────────────────────────────────

class ConcoursListSerializer(serializers.ModelSerializer):
    nombre_matieres = serializers.SerializerMethodField()
    nombre_inscrits = serializers.SerializerMethodField()

    class Meta:
        model = Concours
        fields = [
            'id', 'nom', 'description',
            'inscription_prepa', 'montant_prepa',
            'date_debut', 'date_fin',
            'nombre_matieres', 'nombre_inscrits',
        ]

    def get_nombre_matieres(self, obj) -> int:
        return obj.matiere_concours.count()

    def get_nombre_inscrits(self, obj) -> int:
        return obj.inscriptions.filter(status='validee').count()


class ConcoursDetailSerializer(serializers.ModelSerializer):
    matieres = serializers.SerializerMethodField()
    nombre_inscrits = serializers.SerializerMethodField()
    sessions = serializers.SerializerMethodField()

    class Meta:
        model = Concours
        fields = [
            'id', 'nom', 'description',
            'inscription_prepa', 'montant_prepa',
            'date_debut', 'date_fin',
            'matieres', 'sessions', 'nombre_inscrits',
        ]

    def get_matieres(self, obj):
        matiere_concours = obj.matiere_concours.select_related('matiere').all()
        return [
            {
                "id": str(mc.matiere.id),
                "nom": mc.matiere.nom,
                "description": mc.matiere.description,
                "coefficient": mc.coefficient,
            }
            for mc in matiere_concours
        ]

    def get_nombre_inscrits(self, obj) -> int:
        return obj.inscriptions.filter(status='validee').count()

    def get_sessions(self, obj):
        return SessionSerializer(obj.sessions.all(), many=True).data

class MatiereCoefficientInput(serializers.Serializer):
    matiere_id = serializers.UUIDField()
    coefficient = serializers.IntegerField(min_value=1)

class MatiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matiere
        fields = ['id','nom','description']

class ConcoursCreateSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    inscription_prepa = serializers.IntegerField(min_value=0)
    montant_prepa = serializers.IntegerField(min_value=0)
    date_debut = serializers.DateField()
    date_fin = serializers.DateField()
    matieres = MatiereCoefficientInput(many=True)  # liste de matières avec coefficients

    def validate(self, data):
        # Vérifier que date_fin > date_debut
        if data['date_fin'] <= data['date_debut']:
            raise serializers.ValidationError({
                "date_fin": "La date de fin doit être après la date de début."
            })

        # Vérifier que montant_prepa >= inscription_prepa
        if data['montant_prepa'] < data['inscription_prepa']:
            raise serializers.ValidationError({
                "montant_prepa": "Le montant total doit être supérieur ou égal au montant d'inscription."
            })

        # Vérifier que toutes les matières existent
        for item in data['matieres']:
            if not Matiere.objects.filter(id=item['matiere_id']).exists():
                raise serializers.ValidationError({
                    "matieres": f"Matière {item['matiere_id']} introuvable."
                })

        return data

    def create(self, validated_data):
        matieres_data = validated_data.pop('matieres')

        # Créer le concours
        concours = Concours.objects.create(**validated_data)

        # Associer les matières avec leurs coefficients
        for item in matieres_data:
            MatiereConcours.objects.create(
                concours=concours,
                matiere_id=item['matiere_id'],
                coefficient=item['coefficient'],
            )

        return concours

    def update(self, instance, validated_data):
        matieres_data = validated_data.pop('matieres', None)

        # Mettre à jour les champs simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Mettre à jour les matières si fournies
        if matieres_data is not None:
            # Supprimer les anciennes associations
            instance.matiere_concours.all().delete()
            # Recréer les nouvelles
            for item in matieres_data:
                MatiereConcours.objects.create(
                    concours=instance,
                    matiere_id=item['matiere_id'],
                    coefficient=item['coefficient'],
                )

        return instance


# ───────────────────────────────────────────
# SESSION
# ───────────────────────────────────────────

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'nom', 'date', 'concours']


# ───────────────────────────────────────────
# INSCRIPTION
# ───────────────────────────────────────────

class InscriptionSerializer(serializers.ModelSerializer):
    concours = ConcoursListSerializer(read_only=True)
    concours_id = serializers.UUIDField(write_only=True)
    total_paye = serializers.SerializerMethodField()
    reste_a_payer = serializers.SerializerMethodField()

    class Meta:
        model = Inscription
        fields = [
            'id', 'concours', 'concours_id',
            'status', 'created_at',
            'total_paye', 'reste_a_payer',
        ]
        read_only_fields = ['status', 'created_at']

    def get_total_paye(self, obj) -> int:
        total = obj.paiements.aggregate(Sum('montant'))['montant__sum']
        return total or 0

    def get_reste_a_payer(self, obj) -> int:
        total_paye = self.get_total_paye(obj)
        return max(0, obj.concours.montant_prepa +obj.concours.inscription_prepa - total_paye)

    def validate_concours_id(self, value):
        if not Concours.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ce concours n'existe pas.")
        return value

    def create(self, validated_data):
        eleve = self.context['request'].user_obj 
        concours_id = validated_data['concours_id']

        # Vérifier que l'élève n'est pas déjà inscrit
        if Inscription.objects.filter(eleve=eleve, concours_id=concours_id).exists():
            raise serializers.ValidationError("Vous êtes déjà inscrit à ce concours.")

        return Inscription.objects.create(
            eleve=eleve,
            concours_id=concours_id,
            status='en_attente',
        )
# ───────────────────────────────────────────
# PAIEMENT
# ───────────────────────────────────────────

class PaiementSerializer(serializers.ModelSerializer):
    inscription_id = serializers.UUIDField(write_only=True)
    total_paye = serializers.SerializerMethodField()
    reste_a_payer = serializers.SerializerMethodField()

    class Meta:
        model = Paiement
        fields = [
            'id', 'inscription_id', 'montant',
            'statut', 'created_at',
            'total_paye', 'reste_a_payer',
        ]
        read_only_fields = ['statut', 'created_at']

    def get_total_paye(self, obj) -> int:
        total = Paiement.objects.filter(
            inscription=obj.inscription
        ).aggregate(Sum('montant'))['montant__sum']
        return total or 0

    def get_reste_a_payer(self, obj) -> int:
        total_paye = self.get_total_paye(obj)
        return max(0, obj.inscription.concours.montant_prepa +obj.inscription.concours.inscription_prepa - total_paye)

    def validate(self, data):
        inscription_id = data.get('inscription_id')
        montant = data.get('montant')

        try:
            inscription = Inscription.objects.get(id=inscription_id)
        except Inscription.DoesNotExist:
            raise serializers.ValidationError({
                "inscription_id": "Inscription introuvable."
            })

        # Vérifier que le paiement ne dépasse pas le montant total
        total_paye = Paiement.objects.filter(
            inscription=inscription
        ).aggregate(Sum('montant'))['montant__sum'] or 0

        if total_paye >= inscription.concours.montant_prepa+inscription.concours.inscription_prepa:
            raise serializers.ValidationError({
                "montant": "Ce concours est déjà entièrement payé."
            })

        data['inscription'] = inscription
        return data

    def create(self, validated_data):
        validated_data.pop('inscription_id')
        return Paiement.objects.create(**validated_data)

class SessionSerializer(serializers.ModelSerializer):
    concours = ConcoursListSerializer(read_only=True)
    concours_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Session
        fields = ['id', 'nom', 'date', 'concours', 'concours_id']

    def validate_concours_id(self, value):
        if not Concours.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ce concours n'existe pas.")
        return value

    def create(self, validated_data):
        return Session.objects.create(**validated_data)

class NoteSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.SerializerMethodField()
    prof_nom = serializers.SerializerMethodField()
    matiere_nom = serializers.SerializerMethodField()
    session_nom = serializers.SerializerMethodField()

    # Champs write_only pour la création
    eleve_id = serializers.UUIDField(write_only=True)
    prof_id = serializers.UUIDField(write_only=True)
    session_id = serializers.UUIDField(write_only=True)
    matiere_concours_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Note
        fields = [
            'id', 'valeur', 'created_at',
            'eleve_id', 'prof_id', 'session_id', 'matiere_concours_id',
            'eleve_nom', 'prof_nom', 'matiere_nom', 'session_nom',
        ]
        read_only_fields = ['created_at']

    def get_eleve_nom(self, obj) -> str:
        return f"{obj.eleve.prenom} {obj.eleve.nom}"

    def get_prof_nom(self, obj) -> str:
        if obj.prof:
            return f"{obj.prof.prenom} {obj.prof.nom}"
        return "N/A"

    def get_matiere_nom(self, obj) -> str:
        if obj.matiere_concours:
            return obj.matiere_concours.matiere.nom
        return "N/A"

    def get_session_nom(self, obj) -> str:
        return obj.session.nom

    # def validate_valeur(self, value):
    #     if value < 0 or value > 20:
    #         raise serializers.ValidationError("La note doit être entre 0 et 20.")
    #     return value

    def validate(self, data):
        # Vérifier que l'élève existe
        try:
            eleve = Eleve.objects.get(id=data['eleve_id'])
        except Eleve.DoesNotExist:
            raise serializers.ValidationError({"eleve_id": "Élève introuvable."})

        # Vérifier que le prof existe
        try:
            prof = Prof.objects.get(id=data['prof_id'])
        except Prof.DoesNotExist:
            raise serializers.ValidationError({"prof_id": "Professeur introuvable."})

        # Vérifier que la session existe
        try:
            session = Session.objects.get(id=data['session_id'])
        except Session.DoesNotExist:
            raise serializers.ValidationError({"session_id": "Session introuvable."})

        # Vérifier que la matière_concours existe
        try:
            matiere_concours = MatiereConcours.objects.get(id=data['matiere_concours_id'])
        except MatiereConcours.DoesNotExist:
            raise serializers.ValidationError({"matiere_concours_id": "Matière introuvable."})

        # Vérifier qu'une note n'existe pas déjà pour cet élève/session/matière
        if Note.objects.filter(
            eleve=eleve,
            session=session,
            matiere_concours=matiere_concours
        ).exists():
            raise serializers.ValidationError(
                "Une note existe déjà pour cet élève dans cette session et cette matière."
            )

        # Injecter les objets résolus
        data['eleve'] = eleve
        data['prof'] = prof
        data['session'] = session
        data['matiere_concours'] = matiere_concours
        return data

    def create(self, validated_data):
        # Supprimer les champs UUID bruts, on a déjà les objets
        validated_data.pop('eleve_id')
        validated_data.pop('prof_id')
        validated_data.pop('session_id')
        validated_data.pop('matiere_concours_id')
        return Note.objects.create(**validated_data)


class NoteUpdateSerializer(serializers.ModelSerializer):
    """Serializer léger uniquement pour modifier la valeur d'une note"""
    class Meta:
        model = Note
        fields = ['valeur']

    # def validate_valeur(self, value):
    #     if value < 0 or value > 20:
    #         raise serializers.ValidationError("La note doit être entre 0 et 20.")
    #     return value


# ───────────────────────────────────────────
# SESSION
# ───────────────────────────────────────────

class SessionSerializer(serializers.ModelSerializer):
    concours_nom = serializers.SerializerMethodField()
    concours_id = serializers.UUIDField(write_only=True)
    nombre_notes = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'nom', 'date',
            'concours_id', 'concours_nom',
            'nombre_notes',
        ]

    def get_concours_nom(self, obj) -> str:
        if obj.concours:
            return obj.concours.nom
        return "N/A"

    def get_nombre_notes(self, obj) -> int:
        return obj.notes.count()

    def validate_concours_id(self, value):
        if not Concours.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ce concours n'existe pas.")
        return value

    def create(self, validated_data):
        return Session.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ───────────────────────────────────────────
# ANNONCE
# ───────────────────────────────────────────

class AnnonceSerializer(serializers.ModelSerializer):
    admin_nom = serializers.SerializerMethodField()
    admin_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Annonce
        fields = [
            'id', 'titre', 'contenu', 'type',
            'is_public', 'created_at',
            'admin_id', 'admin_nom',
        ]
        read_only_fields = ['created_at']

    def get_admin_nom(self, obj) -> str:
        if obj.admin:
            return f"{obj.admin.prenom} {obj.admin.nom}"
        return "N/A"

    def create(self, validated_data):
        # L'admin est injecté depuis la vue
        admin = self.context.get('admin')
        validated_data.pop('admin_id', None)
        return Annonce.objects.create(admin=admin, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('admin_id', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance