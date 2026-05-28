from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Note, Inscription, Session, MatiereConcours

@api_view(['GET'])
def resultats_concours_public(request, session_id):
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({"erreur": "Session introuvable"}, status=404)

    # Même code que votre vue authentifiée (resultats_concours)
    matieres_concours = MatiereConcours.objects.filter(concours=session.concours)
    matiere_noms = [mc.matiere.nom for mc in matieres_concours]
    matiere_ids = {mc.id: mc.matiere.nom for mc in matieres_concours}

    inscriptions = Inscription.objects.filter(session=session).select_related('eleve')
    notes = Note.objects.filter(session=session).select_related('eleve', 'matiere_concours__matiere')

    notes_par_eleve = {}
    for note in notes:
        eleve_id = note.eleve.id
        if eleve_id not in notes_par_eleve:
            notes_par_eleve[eleve_id] = {}
        matiere_nom = matiere_ids.get(note.matiere_concours.id, "Inconnue")
        notes_par_eleve[eleve_id][matiere_nom] = note.valeur

    eleves_data = []
    for insc in inscriptions:
        eleve = insc.eleve
        notes_eleve = {nom: None for nom in matiere_noms}
        if eleve.id in notes_par_eleve:
            notes_eleve.update(notes_par_eleve[eleve.id])

        total = sum(v for v in notes_eleve.values() if v is not None)
        eleves_data.append({
            "nom": eleve.nom,
            "prenom": eleve.prenom,
            "notes": notes_eleve,
            "total": total,
            "rang": 0
        })

    eleves_data.sort(key=lambda e: (e['nom'].lower(), e['prenom'].lower()))
    eleves_tries_par_total = sorted(eleves_data, key=lambda e: e['total'], reverse=True)
    for i, e in enumerate(eleves_tries_par_total, 1):
        e['rang'] = i
    eleves_data.sort(key=lambda e: (e['nom'].lower(), e['prenom'].lower()))

    return Response({
        "session": {"id": session.id, "nom": session.nom},
        "matieres": matiere_noms,
        "eleves": eleves_data
    })
