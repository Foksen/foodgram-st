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


class UserRepresentationSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True)
    avatar = serializers.SerializerMethodField(read_only=True)

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

    def get_avatar(self, user):
        if user.avatar:
            return user.avatar.url
        return None


class CustomUserSerializer(UserSerializer):
    id = serializers.ReadOnlyField()
    username = serializers.ReadOnlyField()
    first_name = serializers.ReadOnlyField()
    last_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.SerializerMethodField(read_only=True)

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

    def get_avatar(self, user):
        if user.avatar:
            return user.avatar.url
        return None

    def to_representation(self, user):
        representation_serializer = UserRepresentationSerializer(
            instance=user, context=self.context
        )
        representation_data = representation_serializer.data
        representation_data["is_subscribed"] = self.get_is_subscribed(user)
        representation_data["avatar"] = self.get_avatar(user)
        return representation_data


class SetAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ("avatar",)


class SubscribedAuthorRepresentationSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True)
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.IntegerField(read_only=True)

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

    def get_recipes(self, obj):
        return []


class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields

    def get_image(self, recipe):
        if recipe.image:
            return recipe.image.url
        return ""


class SubscribedAuthorSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

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

    def get_is_subscribed(self, user):
        request = self.context.get("request")
        return (
            request is not None
            and not request.user.is_anonymous
            and Subscription.objects.filter(
                subscriber=request.user, author=user
            ).exists()
        )

    def get_avatar(self, user):
        if user.avatar:
            return user.avatar.url
        return None

    def get_recipes(self, author):
        request = self.context.get("request")
        recipes = author.recipes.all()

        recipes_limit = None

        query_has_limit = (
            request
            and hasattr(request, "query_params")
            and request.query_params.get("recipes_limit")
        )
        if query_has_limit:
            try:
                recipes_limit = int(request.query_params.get("recipes_limit"))
            except (ValueError, TypeError):
                pass

        get_has_limit = (
            recipes_limit is None
            and request
            and hasattr(request, "GET")
            and request.GET.get("recipes_limit")
        )
        if get_has_limit:
            try:
                recipes_limit = int(request.GET.get("recipes_limit"))
            except (ValueError, TypeError):
                pass

        if recipes_limit is None and "recipes_limit" in self.context:
            try:
                recipes_limit = int(self.context.get("recipes_limit"))
            except (ValueError, TypeError):
                pass

        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]

        serialized_recipes = RecipeShortSerializer(
            recipes, many=True, context={"request": request}
        ).data

        if serialized_recipes is None:
            return []

        return serialized_recipes

    def get_recipes_count(self, author):
        return author.recipes.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "recipes" not in data:
            data["recipes"] = self.get_recipes(instance)
        if "recipes_count" not in data:
            data["recipes_count"] = self.get_recipes_count(instance)
        return data


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
        read_only_fields = ("id", "name", "measurement_unit", "amount")


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
    image = Base64ImageField(read_only=True)
    name = serializers.ReadOnlyField()
    text = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

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
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).exists()

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientCreateSerializer(many=True)
    cooking_time = serializers.IntegerField(min_value=1)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "ingredients", "image", "name", "text", "cooking_time")

    def validate(self, recipe_data):
        if not recipe_data.get("name"):
            raise serializers.ValidationError(
                {"name": "Название рецепта обязательно"}
            )
        if not recipe_data.get("text"):
            raise serializers.ValidationError(
                {"text": "Описание рецепта обязательно"}
            )
        if not recipe_data.get("cooking_time"):
            raise serializers.ValidationError(
                {"cooking_time": "Время приготовления обязательно"}
            )
        if "image" not in recipe_data or not recipe_data.get("image"):
            raise serializers.ValidationError(
                {"image": "Изображение рецепта обязательно"}
            )
        return recipe_data

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create(
            [
                IngredientRecipe(
                    recipe=recipe,
                    ingredient=ingredient["id"],
                    amount=ingredient["amount"],
                )
                for ingredient in ingredients
            ]
        )

    def create(self, validated_data):
        author = self.context.get("request").user
        ingredients = validated_data.pop("ingredients", [])
        validated_data["author"] = author

        recipe = super().create(validated_data)

        if ingredients:
            self.create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients")
        instance.ingredients.clear()
        self.create_ingredients(ingredients, instance)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
