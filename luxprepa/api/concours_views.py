import jwt
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Concours, Inscription, Paiement, Eleve, User,Activite
from .serializers import (
    ConcoursListSerializer, ConcoursDetailSerializer, ConcoursCreateSerializer,
    InscriptionSerializer, PaiementSerializer, SessionSerializer
)

def verifier_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_user_from_token(request):
    payload = verifier_token(request)
    if payload is None:
        return None
    try:
        return User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return None


def reponse_non_autorise():
    return Response(
        {"erreur": "Token invalide ou expiré. Veuillez vous reconnecter."},
        status=status.HTTP_401_UNAUTHORIZED
    )


def reponse_admin_requis():
    return Response(
        {"erreur": "Accès réservé aux administrateurs."},
        status=status.HTTP_403_FORBIDDEN
    )

class ConcoursListView(APIView):
    def get(self, request):
        concours = Concours.objects.all().order_by('date_debut')
        serializer = ConcoursListSerializer(concours, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # Vérifier que c'est un admin
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()

        serializer = ConcoursCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        concours = serializer.save()
        return Response(
            {
                "message": "Concours créé avec succès.",
                "concours": ConcoursDetailSerializer(concours).data,
            },
            status=status.HTTP_201_CREATED
        )


class ConcoursDetailView(APIView):

    def get(self, request, concours_id):
        concours = get_object_or_404(Concours, id=concours_id)
        serializer = ConcoursDetailSerializer(concours)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, concours_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()

        concours = get_object_or_404(Concours, id=concours_id)
        serializer = ConcoursCreateSerializer(
            concours,
            data=request.data,
            partial=True  # permet de ne modifier que certains champs
        )
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        concours = serializer.save()
        return Response(
            {
                "message": "Concours modifié avec succès.",
                "concours": ConcoursDetailSerializer(concours).data,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, concours_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()

        concours = get_object_or_404(Concours, id=concours_id)
        concours.delete()
        return Response(
            {"message": "Concours supprimé avec succès."},
            status=status.HTTP_200_OK
        )

class InscriptionListView(APIView):

    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        # Base queryset
        if user.role == 'admin' or user.role == 'prof':
            queryset = Inscription.objects.all().select_related('concours', 'eleve')
        else:
            try:
                eleve = Eleve.objects.get(id=user.id)
            except Eleve.DoesNotExist:
                return Response(
                    {"erreur": "Profil élève introuvable."},
                    status=status.HTTP_404_NOT_FOUND
                )
            queryset = Inscription.objects.filter(eleve=eleve).select_related('concours')

        # Filtre optionnel par concours
        concours_id = request.query_params.get('concours')  # ou 'concours_id' selon votre convention
        if concours_id:
            queryset = queryset.filter(concours_id=concours_id)

        serializer = InscriptionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'eleve':
            return Response(
                {"erreur": "Seuls les élèves peuvent s'inscrire à un concours."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            eleve = Eleve.objects.get(id=user.id)
        except Eleve.DoesNotExist:
            return Response(
                {"erreur": "Profil élève introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        # On injecte l'élève dans le contexte pour le serializer
        serializer = InscriptionSerializer(
            data=request.data,
            context={'request': request, 'user_obj': eleve}
        )

        # Surcharge du contexte pour passer user_obj
        serializer.context['request'].user_obj = eleve

        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        inscription = serializer.save()
        return Response(
            {
                "message": "Inscription enregistrée avec succès.",
                "inscription": InscriptionSerializer(inscription).data,
            },
            status=status.HTTP_201_CREATED
        )


class InscriptionDetailView(APIView):
    def get(self, request, inscription_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        inscription = get_object_or_404(Inscription, id=inscription_id)

        # Un élève ne peut voir que sa propre inscription
        if user.role == 'eleve' and str(inscription.eleve.id) != str(user.id):
            return Response(
                {"erreur": "Accès non autorisé."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InscriptionSerializer(inscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, inscription_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        inscription = get_object_or_404(Inscription, id=inscription_id)

        # Seul l'élève concerné ou un admin peut annuler
        if user.role == 'eleve' and str(inscription.eleve.id) != str(user.id):
            return Response(
                {"erreur": "Accès non autorisé."},
                status=status.HTTP_403_FORBIDDEN
            )

        inscription.status = 'annulee'
        inscription.save()
        return Response(
            {"message": "Inscription annulée."},
            status=status.HTTP_200_OK
        )


class ValiderInscriptionView(APIView):

    def patch(self, request, inscription_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()

        inscription = get_object_or_404(Inscription, id=inscription_id)
        inscription.status = 'validee'
        inscription.save()
        Activite.objects.create(
            type_act='inscription',
            message = f"Inscription de {inscription.eleve.prenom} {inscription.eleve.nom} confirmée - {inscription.concours.nom}"
        )

        return Response(
            {
                "message": "Inscription validée avec succès.",
                "inscription": InscriptionSerializer(inscription).data,
            },
            status=status.HTTP_200_OK
        )

class PaiementListView(APIView):
 
    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        if user.role == 'admin':
            paiements = Paiement.objects.all().select_related('inscription')
        else:
            paiements = Paiement.objects.filter(
                inscription__eleve__id=user.id
            ).select_related('inscription')

        serializer = PaiementSerializer(paiements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return Response(
                {"erreur": "Seuls les administrateurs peuvent effectuer des paiements."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PaiementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        paiement = serializer.save()
        return Response(
            {
                "message": "Versement enregistré avec succès.",
                "paiement": PaiementSerializer(paiement).data,
            },
            status=status.HTTP_201_CREATED
        )