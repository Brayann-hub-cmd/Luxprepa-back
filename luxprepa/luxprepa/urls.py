from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from api.resultat_views import PublierResultatsView, ResultatsPublicView
urlpatterns = [
    path('api/',include("api.urls")),
    # path('sessions/<uuid:session_id>/publier/', PublierResultatsView.as_view(), name='publier-resultats'),
    # path('resultats/<str:token>/', ResultatsPublicView.as_view(), name='resultats-public'),
] + static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)