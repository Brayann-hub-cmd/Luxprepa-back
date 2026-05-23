from rest_framework.response import Response
from rest_framework import status
from .models import User, MatiereConcours
from .serializers import MatiereConcourSerializer
from .concours_views import get_user_from_token,get_object_or_404,reponse_non_autorise,reponse_admin_requis
from rest_framework.views import APIView

class MatiereConcourListView(APIView):
    def get(self,request):
        mc = MatiereConcours.objects.all().select_related('matiere','concours')
        serializer = MatiereConcourSerializer(mc,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def post(self,request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role !='admin':
            return reponse_admin_requis()
        
        serializer = MatiereConcourSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"erreurs":serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        mc = serializer.save()
        return Response(
            {
                "message":"Matiere ajoutée au concour avec succès.",
                "matiere_concours":MatiereConcourSerializer(mc).data
            },status=status.HTTP_201_CREATED
        )
    
class MatiereConcourDetailView(APIView):
    def get(self,request,id_mc):
        mc = get_object_or_404(MatiereConcours,id=id_mc)
        return Response(MatiereConcourSerializer(mc).data,status=status.HTTP_200_OK)
    
    def patch(self,request,id_mc):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role !='admin':
            return reponse_admin_requis()
        mc = get_object_or_404(MatiereConcours,id=id_mc)
        coefficient = request.data.get('coefficient')
        if not coefficient:
            return Response(
                {"erreur":"Le coefficient est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        mc.coefficient = coefficient
        mc.save()
        return Response(
            {
                "message":"Coefficient modifié avec succès.",
                "matiere_concours":MatiereConcourSerializer(mc).data
            },status=status.HTTP_200_OK
        )
    
    def delete(self, request,id_mc):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role !='admin':
            return reponse_admin_requis()
        mc = get_object_or_404(MatiereConcours,id=id_mc)
        mc.delete()
        return Response(
            {"message":"Matière rétirée du concours avec succès."},
            status=status.HTTP_200_OK
        )
