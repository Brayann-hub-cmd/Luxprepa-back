import jwt
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Note, Session, Annonce, User, Eleve, Prof, Admin, Inscription, Paiement
from .serializers import NoteSerializer, NoteUpdateSerializer, SessionSerializer, AnnonceSerializer

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
        {"erreur": "Token invalide ou expiré."},
        status=status.HTTP_401_UNAUTHORIZED
    )


def reponse_acces_refuse():
    return Response(
        {"erreur": "Vous n'avez pas les droits pour effectuer cette action."},
        status=status.HTTP_403_FORBIDDEN
    )


def eleve_a_tout_paye(eleve):
    inscriptions = Inscription.objects.filter(eleve=eleve, status='validee')
    for inscription in inscriptions:
        total_paye = inscription.paiements.aggregate(
            total=__import__('django.db.models', fromlist=['Sum']).Sum('montant')
        )['total'] or 0
        if total_paye >= inscription.concours.montant_prepa + inscription.concours.inscription_prepa:
            return True
    return False

class NoteListView(APIView):
    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        if user.role == 'eleve':
            notes = Note.objects.filter(eleve__id=user.id).select_related(
                'eleve', 'prof', 'session', 'matiere_concours__matiere'
            )
        else:
            notes = Note.objects.all().select_related(
                'eleve', 'prof', 'session', 'matiere_concours__matiere'
            )

        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        # Seuls les profs et admins peuvent affecter des notes
        if user.role not in ('prof', 'admin'):
            return reponse_acces_refuse()

        serializer = NoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = serializer.save()
        return Response(
            {
                "message": "Note affectée avec succès.",
                "note": NoteSerializer(note).data,
            },
            status=status.HTTP_201_CREATED
        )


class NoteDetailView(APIView):
    def get(self, request, note_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        note = get_object_or_404(Note, id=note_id)

        # Un élève ne peut voir que ses propres notes
        if user.role == 'eleve' and str(note.eleve.id) != str(user.id):
            return reponse_acces_refuse()

        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, note_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role not in ('prof', 'admin'):
            return reponse_acces_refuse()

        note = get_object_or_404(Note, id=note_id)

        # Un prof ne peut modifier que ses propres notes
        if user.role == 'prof' and (note.prof is None or str(note.prof.id) != str(user.id)):
            return reponse_acces_refuse()

        serializer = NoteUpdateSerializer(note, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = serializer.save()
        return Response(
            {
                "message": "Note modifiée avec succès.",
                "note": NoteSerializer(note).data,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, note_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        note = get_object_or_404(Note, id=note_id)
        note.delete()
        return Response(
            {"message": "Note supprimée avec succès."},
            status=status.HTTP_200_OK
        )
class SessionListView(APIView):

    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        sessions = Session.objects.all().select_related('concours').order_by('date')
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        serializer = SessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = serializer.save()
        return Response(
            {
                "message": "Session créée avec succès.",
                "session": SessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED
        )


class SessionDetailView(APIView):

    def get(self, request, session_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()

        session = get_object_or_404(Session, id=session_id)
        serializer = SessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, session_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        session = get_object_or_404(Session, id=session_id)
        serializer = SessionSerializer(session, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = serializer.save()
        return Response(
            {
                "message": "Session modifiée avec succès.",
                "session": SessionSerializer(session).data,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, session_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        session = get_object_or_404(Session, id=session_id)
        session.delete()
        return Response(
            {"message": "Session supprimée avec succès."},
            status=status.HTTP_200_OK
        )

class AnnonceListView(APIView):

    def get(self, request):
        user = get_user_from_token(request)

        if user is None:
            # Non connecté → uniquement les annonces publiques
            annonces = Annonce.objects.filter(is_public=True).order_by('-created_at')

        elif user.role == 'admin':
            # Admin → toutes les annonces
            annonces = Annonce.objects.all().order_by('-created_at')

        elif user.role == 'prof':
            # Prof → toutes les annonces
            annonces = Annonce.objects.all().order_by('-created_at')

        elif user.role == 'eleve':
            try:
                eleve = Eleve.objects.get(id=user.id)
                if eleve_a_tout_paye(eleve):
                    # Élève ayant tout payé → toutes les annonces
                    annonces = Annonce.objects.all().order_by('-created_at')
                else:
                    # Élève n'ayant pas tout payé → uniquement publiques
                    annonces = Annonce.objects.filter(is_public=True).order_by('-created_at')
            except Eleve.DoesNotExist:
                annonces = Annonce.objects.filter(is_public=True).order_by('-created_at')
        else:
            annonces = Annonce.objects.filter(is_public=True).order_by('-created_at')

        serializer = AnnonceSerializer(annonces, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        try:
            admin = Admin.objects.get(id=user.id)
        except Admin.DoesNotExist:
            return Response(
                {"erreur": "Profil admin introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AnnonceSerializer(data=request.data, context={'admin': admin,'request':request})
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        annonce = serializer.save()
        return Response(
            {
                "message": "Annonce créée avec succès.",
                "annonce": AnnonceSerializer(annonce,context={'request':request}).data,
            },
            status=status.HTTP_201_CREATED
        )


class AnnonceDetailView(APIView):

    def get(self, request, annonce_id):
        annonce = get_object_or_404(Annonce, id=annonce_id)
        user = get_user_from_token(request)

        # Annonce privée → vérifier les droits
        if not annonce.is_public:
            if user is None:
                return reponse_non_autorise()
            if user.role == 'eleve':
                try:
                    eleve = Eleve.objects.get(id=user.id)
                    if not eleve_a_tout_paye(eleve):
                        return reponse_acces_refuse()
                except Eleve.DoesNotExist:
                    return reponse_acces_refuse()

        serializer = AnnonceSerializer(annonce)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, annonce_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        annonce = get_object_or_404(Annonce, id=annonce_id)
        serializer = AnnonceSerializer(annonce, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"erreurs": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        annonce = serializer.save()
        return Response(
            {
                "message": "Annonce modifiée avec succès.",
                "annonce": AnnonceSerializer(annonce).data,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, annonce_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_acces_refuse()

        annonce = get_object_or_404(Annonce, id=annonce_id)
        annonce.delete()
        return Response(
            {"message": "Annonce supprimée avec succès."},
            status=status.HTTP_200_OK
        )