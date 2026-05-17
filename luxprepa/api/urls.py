from django.urls import path
from .views import (
    # Auth
    InscriptionView, ConnexionView, ProfilView, DeconnexionView,
)
from .concours_views import (
    ConcoursListView, ConcoursDetailView,
    InscriptionListView, InscriptionDetailView, ValiderInscriptionView,
    PaiementListView,
)

urlpatterns = [
    # ── Auth ──
    path('auth/inscription/', InscriptionView.as_view(), name='inscription'),
    path('auth/connexion/', ConnexionView.as_view(), name='connexion'),
    path('auth/profil/', ProfilView.as_view(), name='profil'),
    path('auth/deconnexion/', DeconnexionView.as_view(), name='deconnexion'),

    # ── Concours ──
    path('concours/', ConcoursListView.as_view(), name='concours-list'),
    path('concours/<uuid:concours_id>/', ConcoursDetailView.as_view(), name='concours-detail'),

    # ── Inscriptions ──
    path('inscriptions/', InscriptionListView.as_view(), name='inscription-list'),
    path('inscriptions/<uuid:inscription_id>/', InscriptionDetailView.as_view(), name='inscription-detail'),
    path('inscriptions/<uuid:inscription_id>/valider/', ValiderInscriptionView.as_view(), name='inscription-valider'),

    # ── Paiements ──
    path('paiements/', PaiementListView.as_view(), name='paiement-list'),
]