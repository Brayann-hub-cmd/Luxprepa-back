from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from api.resultat_views import resultats_concours_public
urlpatterns = [
    path('api/',include("api.urls")),
     path('api/resultats-public/<uuid:session_id>/', resultats_concours_public),  
] + static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)