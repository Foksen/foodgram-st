from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Recipe


class RecipeViewSet(viewsets.GenericViewSet):
    all_recipes = Recipe.objects.all()

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[AllowAny]
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        return Response(
            {"short-link": f'/api/recipes/{recipe.id}/'},
            status=status.HTTP_200_OK
        )
