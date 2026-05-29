from django.urls import path
from .views import (
    # Auth
    InscriptionView, ConnexionView, ProfilView, DeconnexionView,EleveListView,EleveDetailView,UsersListView,UsersDetailView,
    InscriptionAdminCreateView
)
from .concours_views import (
    ConcoursListView, ConcoursDetailView,
    InscriptionListView, InscriptionDetailView, ValiderInscriptionView,
    PaiementListView,
)
from .notes_views import (
    NoteListView, NoteDetailView,
    SessionListView, SessionDetailView,
    AnnonceListView, AnnonceDetailView,NoteBatchCreateView
)
from .pre_inscription_views import (PreInscriptionView,ConfirmationSMSView,RenvoyerCodeView)
from .pwd_views import (ChangerMotDePasseView,MotDePasseOublieView,VerifierCodeResetView,NouveauMotDePasseView)
from .matiere_views import MatiereDetailView,MatiereListView
from .matiere_concours_views import MatiereConcourDetailView,MatiereConcourListView,MatiereConcoursListView
from .activite_views import ActiviteListView
from .resultat_views import resultats_concours_public 


urlpatterns = [
    # ── Auth ──
    path('auth/inscription/', InscriptionView.as_view(), name='inscription'),
    path('auth/connexion/', ConnexionView.as_view(), name='connexion'),
    path('auth/profil/', ProfilView.as_view(), name='profil'),
    path('auth/deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('auth/pre-inscription/', PreInscriptionView.as_view()),
    path('auth/confirmer/', ConfirmationSMSView.as_view()),
    path('auth/renvoyer-code/', RenvoyerCodeView.as_view()),
    # Changer mot de passe (connecté)
    path('auth/changer-password/', ChangerMotDePasseView.as_view()),
    # Mot de passe oublié (3 étapes)
    path('auth/mot-de-passe-oublie/', MotDePasseOublieView.as_view()),
    path('auth/verifier-code-reset/', VerifierCodeResetView.as_view()),
    path('auth/nouveau-password/', NouveauMotDePasseView.as_view()),
    # ── Matiere ──
    path('matieres/',MatiereListView.as_view(),name='matiere-list'),
    path('matieres/<uuid:id_matiere>/',MatiereDetailView.as_view(),name='matiere-detail'),
    # ── Matiere Concours ──
    path('matiere-concours/',MatiereConcourListView.as_view(),name='matiere-concours-list'),
    path('matiere-concours/<uuid:id_mc>/',MatiereConcourDetailView.as_view(),name='matiere-concours-detail'),
    path('matieres-concours/', MatiereConcoursListView.as_view()),
    # ── Concours ──
    path('concours/', ConcoursListView.as_view(), name='concours-list'),
    path('concours/<uuid:concours_id>/', ConcoursDetailView.as_view(), name='concours-detail'),
    # ── Inscriptions ──
    path('inscriptions/', InscriptionListView.as_view(), name='inscription-list'),
    path('inscriptions/<uuid:inscription_id>/', InscriptionDetailView.as_view(), name='inscription-detail'),
    path('inscriptions/<uuid:inscription_id>/valider/', ValiderInscriptionView.as_view(), name='inscription-valider'),
    # ── Paiements ──
    path('paiements/', PaiementListView.as_view(), name='paiement-list'),
    # ── Sessions ──
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/<uuid:session_id>/', SessionDetailView.as_view(), name='session-detail'),
    # ── notes ──
    path('notes/', NoteListView.as_view(), name='note-list'),
    path('notes/<uuid:note_id>/', NoteDetailView.as_view(), name='note-detail'),
    path('/notes/batch/',NoteBatchCreateView.as_view(),name='notes'),
    # ── Annonces ──
    path('annonces/', AnnonceListView.as_view(), name='annonce-list'),
    path('annonces/<uuid:annonce_id>/', AnnonceDetailView.as_view(), name='annonce-detail'),
    
    path('activites/', ActiviteListView.as_view(), name='activite-list'),
    path('eleves/', EleveListView.as_view(), name='eleve-list'),
    path('eleves/<uuid:id_eleve>/', EleveDetailView.as_view(), name='eleve-detail'),
    path('users/', UsersListView.as_view(), name='eleve-list'),
    path('users/<uuid:id_user>/', UsersDetailView.as_view(), name='eleve-list'),
    path('admin/inscriptions/', InscriptionAdminCreateView.as_view(), name='admin-inscription-create'),
    path('api/resultats-public/<uuid:session_id>/', resultats_concours_public, name='resultats-public'),
]