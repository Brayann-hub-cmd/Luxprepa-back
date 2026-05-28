from rest_framework.response import Response
from rest_framework import status
from .models import Activite
from .serializers import ActiviteSerializer
from .concours_views import get_user_from_token,reponse_non_autorise,reponse_admin_requis
from rest_framework.views import APIView


class ActiviteListView(APIView):

    def get(self, request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()

        activites = Activite.objects.all()[:10]
        serializer = ActiviteSerializer(activites, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)