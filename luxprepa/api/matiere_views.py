from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Matiere
from .serializers import MatiereSerializer
from .concours_views import get_user_from_token,get_object_or_404,reponse_non_autorise,reponse_admin_requis
class MatiereListView(APIView):
    def get(self,request):
        matieres = Matiere.objects.all().order_by('nom')
        serializer = MatiereSerializer(matieres,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def post(self,request):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()
        
        serializer = MatiereSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"erreurs":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
        matiere = serializer.save()
        return Response(
            {"message":"Matiere crée avec succès","matiere":MatiereSerializer(matiere).data},
            status=status.HTTP_201_CREATED
        )
    
class MatiereDetailView(APIView):
    def get(self,request,id_matiere):
        matiere = get_object_or_404(Matiere,id=id_matiere)
        return Response(MatiereSerializer(matiere).data,status=status.HTTP_200_OK)
    
    def put(self,request,id_matiere):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()
        matiere = get_object_or_404(Matiere,id=id_matiere)
        serializer = MatiereSerializer(matiere,data=request.data,partial=True)
        if not serializer.is_valid():
            return Response({"erreurs":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
        matiere = serializer.save()
        return Response(
            {"message":"Matiere modifiée avec succès","matiere":MatiereSerializer(matiere).data},
            status=status.HTTP_200_OK
        )
    
    def delete(self,request,id_matiere):
        user = get_user_from_token(request)
        if user is None:
            return reponse_non_autorise()
        if user.role != 'admin':
            return reponse_admin_requis()
        matiere = get_object_or_404(Matiere,id=id_matiere)
        matiere.delete()
        return Response({"message":"Matière supprimée avec succès"},status=status.HTTP_200_OK)
        