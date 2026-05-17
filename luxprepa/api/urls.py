from django.urls import path
from .views import InscriptionView, ConnexionView, ProfilView, DeconnexionView

urlpatterns = [
    path('v1/auth/inscription/', InscriptionView.as_view(), name='inscription'),
    path('v1/auth/connexion/', ConnexionView.as_view(), name='connexion'),
    path('v1/auth/profil/', ProfilView.as_view(), name='profil'),
    path('v1/auth/deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
]