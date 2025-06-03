from datetime import datetime

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Subscription,
    User,
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import UserPagination, RecipePagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CustomUserSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeReadSerializer,
    SetAvatarSerializer,
    SubscribedAuthorSerializer,
    RecipeShortSerializer,
)


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = UserPagination

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        if request.method == "PUT":
            if not request.data:
                return Response(
                    {"errors": "Отсутствуют данные в запросе"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = SetAvatarSerializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                serializer.data, status=status.HTTP_200_OK
            )

        if request.method == "DELETE":
            request.user.avatar = None
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        current_user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == "POST":
            if current_user == author:
                return Response(
                    {"errors": "Нельзя подписаться на себя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subscription, created = (
                Subscription.objects.get_or_create(
                    subscriber=current_user, author=author
                )
            )

            if not created:
                return Response(
                    {
                        "errors": (
                            f"Вы уже подписаны "
                            f"на автора {author.get_full_name()}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            context = {"request": request}

            serializer = SubscribedAuthorSerializer(
                author, context=context
            )
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )

        if request.method == "DELETE":
            subscription = Subscription.objects.filter(
                subscriber=current_user, author=author
            ).first()

            if not subscription:
                return Response(
                    {
                        "errors": (
                            f"Вы не подписаны на "
                            f"автора {author.get_full_name()}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Приятно видеть, когда в постмане все тесты зелёные,
            # поэтому оставил так
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        current_user = request.user
        subscriptions = User.objects.filter(
            subscribers__subscriber=current_user
        )
        page = self.paginate_queryset(subscriptions)

        context = {"request": request}

        serializer = SubscribedAuthorSerializer(
            page, many=True, context=context
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = (AllowAny,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = (
        Recipe.objects.all()
        .select_related("author")
        .prefetch_related(
            "recipe_ingredients__ingredient",
            "favorite_recipes",
            "shopping_carts",
        )
    )
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeCreateUpdateSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", 'get_link'):
            return [AllowAny()]
        return [IsAuthenticated(), IsAuthorOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _handle_m2m_relation(
        self,
        request,
        pk,
        model_class,
    ):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        verbose_name = model_class._meta.verbose_name

        if request.method == "POST":
            relation, created = model_class.objects.get_or_create(
                user=user, recipe=recipe
            )

            if not created:
                return Response(
                    {
                        "errors": (
                            f'Рецепт "{recipe.name}" '
                            f'уже в {verbose_name}'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )

        relation = model_class.objects.filter(
            user=user, recipe=recipe
        ).first()
        if not relation:
            return Response(
                {
                    "errors": (
                        f'Рецепт "{recipe.name}" '
                        f'не был добавлен в {verbose_name}'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        relation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        return self._handle_m2m_relation(
            request=request,
            pk=pk,
            model_class=Favorite,
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_m2m_relation(
            request=request,
            pk=pk,
            model_class=ShoppingCart,
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            IngredientRecipe.objects.filter(
                recipe__shopping_carts__user=user
            )
            .values(
                "ingredient__name", "ingredient__measurement_unit"
            )
            .annotate(amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        recipes = (
            Recipe.objects.filter(shopping_carts__user=user)
            .select_related("author")
            .order_by("name")
        )

        today = datetime.today()

        shopping_list = "\n".join(
            [
                (
                    f"Список покупок для {user.get_full_name()}\n"
                    f"Дата: {today:%d-%m-%Y}"
                ),
                "Ингредиенты:",
                *[
                    f"{i}. {item['ingredient__name'].capitalize()} "
                    f"({item['ingredient__measurement_unit']}) - "
                    f"{item['amount']}"
                    for i, item in enumerate(ingredients, start=1)
                ],
                "Рецепты:",
                *[
                    f"- {recipe.name} (@ {recipe.author.get_full_name()})"
                    for recipe in recipes
                ],
                f"\nFoodgram ({today:%Y})",
            ]
        )

        filename = f"{user.username}_shopping_list.txt"

        response = HttpResponse(shopping_list, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        if not Recipe.objects.filter(pk=pk).exists():
            return Response(
                {"detail": f"Рецепт с идентификатором {pk} не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        short_link = request.build_absolute_uri(
            reverse("recipe-short-link-redirect", args=[pk])
        )
        return Response({"short-link": short_link})
