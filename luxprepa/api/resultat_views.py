import hashlib
from collections import defaultdict
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Session, Note, LensResultat, Eleve
from .concours_views import get_user_from_token, reponse_non_autorise, reponse_admin_requis
from django.conf import settings

class PublierResultatsView(APIView):

    def post(self, request, session_id):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role not in ('admin', 'prof'):
            return reponse_admin_requis()

        session = get_object_or_404(Session, id=session_id)

        # Générer un token unique basé sur session_id
        token = hashlib.sha256(
            f"{session_id}-{session.nom}".encode()
        ).hexdigest()[:32]

        # Créer ou récupérer le lien
        lien, _ = LensResultat.objects.get_or_create(
            session=session,
            defaults={'token': token}
        )

        lien_url = f"{settings.BACKOFFICE_URL}/resultats/{lien.token}"

        return Response({
            "message": "Résultats publiés avec succès.",
            "lien": lien_url,
            "token": lien.token,
        }, status=status.HTTP_200_OK)


class ResultatsPublicView(APIView):

    def get(self, request, token):
        lien = get_object_or_404(LensResultat, token=token)
        session = lien.session

        # Récupérer toutes les notes de cette session
        notes = Note.objects.filter(
            session=session
        ).select_related('eleve', 'matiere_concours__matiere')

        # Grouper par élève
        eleves_notes = defaultdict(list)
        for note in notes:
            eleves_notes[note.eleve.id].append({
                'matiere': note.matiere_concours.matiere.nom,
                'coefficient': note.matiere_concours.coefficient,
                'valeur': note.valeur,
            })

        # Calculer moyenne pondérée pour chaque élève
        resultats = []
        for eleve_id, notes_list in eleves_notes.items():
            try:
                eleve_obj = Eleve.objects.get(id=eleve_id)
                nom = f"{eleve_obj.prenom} {eleve_obj.nom}"
            except Eleve.DoesNotExist:
                nom = "Inconnu"

            total_points = sum(n['valeur'] * n['coefficient'] for n in notes_list)
            total_coeff = sum(n['coefficient'] for n in notes_list)
            moyenne = round(total_points / total_coeff, 2) if total_coeff > 0 else 0

            resultats.append({
                'eleve_id': str(eleve_id),
                'eleve_nom': nom,
                'notes': notes_list,
                'moyenne': moyenne,
            })

        # Trier par moyenne décroissante et ajouter le rang
        resultats.sort(key=lambda x: x['moyenne'], reverse=True)
        for i, r in enumerate(resultats):
            r['rang'] = i + 1

        return Response({
            'session': {
                'id': str(session.id),
                'nom': session.nom,
                'date': session.date,
                'concours_nom': session.concours.nom if session.concours else '',
            },
            'resultats': resultats,
            'total_eleves': len(resultats),
        }, status=status.HTTP_200_OK)
