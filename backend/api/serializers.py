from rest_framework import serializers
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    User,
    Subscription,
)


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
        )
        read_only_fields = fields

    def get_is_subscribed(self, user):
        request = self.context.get("request")
        return (
            request is not None
            and not request.user.is_anonymous
            and Subscription.objects.filter(
                subscriber=request.user, author=user
            ).exists()
        )


class SetAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ("avatar",)


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


class SubscribedAuthorSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
            "recipes",
            "recipes_count",
        )
        read_only_fields = fields

    def get_recipes(self, author):
        request = self.context.get("request")
        recipes = author.recipes.all()

        recipes_limit = 1000
        try:
            limit_param = request.query_params.get(
                "recipes_limit"
            ) or self.context.get("recipes_limit")
            if limit_param:
                recipes_limit = int(limit_param)
        except (ValueError, TypeError, AttributeError):
            pass

        recipes = recipes[:recipes_limit]
        return RecipeShortSerializer(
            recipes, many=True, context={"request": request}
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )
    amount = serializers.ReadOnlyField()

    class Meta:
        model = IngredientRecipe
        fields = ("id", "name", "measurement_unit", "amount")
        read_only_fields = fields


class IngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = IngredientRecipe
        fields = ("id", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe):
        request = self.context.get("request")
        return bool(
            request
            and not request.user.is_anonymous
            and Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get("request")
        return bool(
            request
            and not request.user.is_anonymous
            and ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).exists()
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientCreateSerializer(many=True, required=True)
    cooking_time = serializers.IntegerField(min_value=1)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ("id", "ingredients", "image", "name", "text", "cooking_time")

    # Для тестов, без него не получается пройти
    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Должен быть указан минимум один ингредиент"
            )

        ingredient_ids = [ingredient["id"].id for ingredient in value]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться"
            )

        return value

    # Required не работает на PATCH (тест), поэтому проверяю вручную
    def validate(self, data):
        if "ingredients" not in data:
            raise serializers.ValidationError(
                {"ingredients": "Должен быть указан минимум один ингредиент"}
            )
        return data

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError("Image cannot be empty.")
        return value

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create(
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient["id"],
                amount=ingredient["amount"],
            )
            for ingredient in ingredients
        )

    def create(self, validated_data):
        author = self.context.get("request").user
        ingredients = validated_data.pop("ingredients", [])
        validated_data["author"] = author

        recipe = super().create(validated_data)

        self.create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)

        if ingredients is not None:
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
