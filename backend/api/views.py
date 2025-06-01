from datetime import datetime

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart,
    Subscription, User
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import UserPagination, RecipePagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CustomUserSerializer, FavoriteSerializer, IngredientSerializer,
    RecipeCreateUpdateSerializer, RecipeReadSerializer,
    SetAvatarSerializer, ShoppingCartSerializer, SubscriptionSerializer
)


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = UserPagination

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        if request.method == 'PUT':
            if not request.data:
                return Response(
                    {'errors': 'Отсутствуют данные в запросе'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = SetAvatarSerializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        if request.method == 'DELETE':
            request.user.avatar = None
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        current_user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if current_user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(
                subscriber=current_user, author=author
            ).exists():
                return Response(
                    {'errors': 'Вы уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription = Subscription.objects.create(
                subscriber=current_user, author=author
            )
            serializer = SubscriptionSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                subscriber=current_user, author=author
            )
            if not subscription.exists():
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        current_user = request.user
        subscriptions = User.objects.filter(
            subscribers__subscriber=current_user
        )

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            subscriptions, many=True, context={'request': request}
        )
        return Response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = (AllowAny,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (IsAuthorOrReadOnly,)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeCreateUpdateSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (AllowAny(),)
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            pk = kwargs.get('pk')
            instance = get_object_or_404(Recipe, pk=pk)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(Recipe, pk=kwargs.get('pk'))

        try:
            self.check_object_permissions(request, instance)
        except Exception as e:
            return Response(
                {'errors': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

        if 'ingredients' not in request.data:
            return Response(
                {'ingredients': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

    def perform_update(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except serializers.ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'errors': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        serializer.save()

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite = Favorite.objects.create(user=user, recipe=recipe)
            serializer = FavoriteSerializer(
                favorite, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        favorite = Favorite.objects.filter(user=user, recipe=recipe)
        if not favorite.exists():
            return Response(
                {'errors': 'Рецепт не был добавлен в избранное'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            shopping_cart = ShoppingCart.objects.create(user=user,
                                                        recipe=recipe)
            serializer = ShoppingCartSerializer(
                shopping_cart, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        shopping_cart = ShoppingCart.objects.filter(user=user, recipe=recipe)
        if not shopping_cart.exists():
            return Response(
                {'errors': 'Рецепт не был добавлен в список покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        shopping_cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_carts__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        if not ingredients:
            return Response(
                {'errors': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )

        today = datetime.today()
        shopping_list = (
            f'Список покупок для {user.get_full_name()}\n\n'
            f'Дата: {today:%d-%m-%Y}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        shopping_list += f'\n\nFoodgram ({today:%Y})'

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(
            shopping_list, content_type='text/plain; charset=UTF-8'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
