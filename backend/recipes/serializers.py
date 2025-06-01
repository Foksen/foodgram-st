import base64

from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from users.serializers import CustomUserSerializer
from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart
)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'name': data['name'],
            'measurement_unit': data['measurement_unit'],
            'amount': data['amount']
        }


class IngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer()
    ingredients = IngredientRecipeSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if data['image'] is None:
            data['image'] = ''

        return {
            'id': data['id'],
            'author': data['author'],
            'ingredients': data['ingredients'],
            'is_favorited': data['is_favorited'],
            'is_in_shopping_cart': data['is_in_shopping_cart'],
            'name': data['name'],
            'image': data['image'],
            'text': data['text'],
            'cooking_time': data['cooking_time']
        }


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientCreateSerializer(many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'image',
            'name', 'text', 'cooking_time'
        )

    def validate(self, attrs):
        if not attrs.get('name'):
            raise serializers.ValidationError(
                {'name': 'Название рецепта обязательно'}
            )
        if not attrs.get('text'):
            raise serializers.ValidationError(
                {'text': 'Описание рецепта обязательно'}
            )
        if not attrs.get('cooking_time'):
            raise serializers.ValidationError(
                {'cooking_time': 'Время приготовления обязательно'}
            )
        return attrs

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Минимум один продукт!'
            )

        ingredient_ids = [item['id'].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Продукты повторяются!'
            )

        for item in value:
            if int(item['amount']) < 1:
                raise serializers.ValidationError(
                    'Количество продукта должно быть не менее 1!'
                )

        return value

    def create_ingredients(self, ingredients, recipe):
        create_ingredients = [
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(create_ingredients)

    def create(self, validated_data):
        author = self.context.get('request').user
        ingredients = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(author=author, **validated_data)

        if ingredients:
            self.create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['image'] is None:
            data['image'] = ''
        return data


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном!'
            )
        ]

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в списке покупок!'
            )
        ]

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data
