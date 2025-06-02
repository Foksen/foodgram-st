from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.NumberFilter(field_name='author__id')

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def filter_is_favorited(self, recipes, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return recipes.filter(favorite_recipes__user=user)
        return recipes

    def filter_is_in_shopping_cart(self, recipes, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return recipes.filter(shopping_carts__user=user)
        return recipes
