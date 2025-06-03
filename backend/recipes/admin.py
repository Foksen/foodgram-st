from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart,
    User, Subscription
)


YES_OR_NO_VARIANTS = (
    ('yes', 'Да'),
    ('no', 'Нет'),
)


class BooleanFilter(admin.SimpleListFilter):
    count_field = None
    annotation_name = None

    def lookups(self, request, model_admin):
        return YES_OR_NO_VARIANTS

    def queryset(self, request, queryset):
        if not self.count_field or not self.annotation_name:
            return queryset

        if self.value() == 'yes':
            return queryset.annotate(**{
                self.annotation_name: Count(self.count_field)
            }).filter(**{f"{self.annotation_name}__gt": 0})
        if self.value() == 'no':
            return queryset.annotate(**{
                self.annotation_name: Count(self.count_field)
            }).filter(**{self.annotation_name: 0})
        return queryset


class HasRecipesFilter(BooleanFilter):
    title = 'есть рецепты'
    parameter_name = 'has_recipes'
    count_field = 'recipes'
    annotation_name = 'recipe_count'


class HasSubscriptionsFilter(BooleanFilter):
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'
    count_field = 'authors'
    annotation_name = 'subscr_count'


class HasSubscribersFilter(BooleanFilter):
    title = 'есть подписчики'
    parameter_name = 'has_subscribers'
    count_field = 'subscribers'
    annotation_name = 'subs_count'


class IsInRecipesFilter(admin.SimpleListFilter):
    title = 'В рецептах'
    parameter_name = 'is_in_recipes'

    def lookups(self, request, model_admin):
        return YES_OR_NO_VARIANTS

    def queryset(self, request, ingredients):
        if self.value() == 'yes':
            return (
                ingredients
                .filter(recipe_ingredients__isnull=False)
                .distinct()
            )
        if self.value() == 'no':
            return ingredients.filter(recipe_ingredients__isnull=True)
        return ingredients


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'get_full_name', 'email', 'get_avatar',
                    'get_recipe_count', 'get_subscription_count',
                    'get_subscriber_count')
    list_filter = (HasRecipesFilter, HasSubscriptionsFilter,
                   HasSubscribersFilter, 'is_staff', 'is_superuser',
                   'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    list_per_page = 20

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email',
                                      'avatar')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups',
                       'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name',
                       'password1', 'password2'),
        }),
    )

    readonly_fields = ['get_avatar']

    def get_queryset(self, request):
        users = super().get_queryset(request)
        return users.annotate(
            recipe_count=Count('recipes', distinct=True),
            subscription_count=Count('authors', distinct=True),
            subscriber_count=Count('subscribers', distinct=True)
        )

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description='Аватар')
    @mark_safe
    def get_avatar(self, obj):
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="80" height="80" />'
        return 'Нет аватара'

    @admin.display(description='Рецептов')
    def get_recipe_count(self, obj):
        return obj.recipe_count

    @admin.display(description='Подписок')
    def get_subscription_count(self, obj):
        return obj.subscription_count

    @admin.display(description='Подписчиков')
    def get_subscriber_count(self, obj):
        return obj.subscriber_count


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'author')
    search_fields = ('subscriber__username', 'author__username')
    list_filter = ('author', 'subscriber')
    list_per_page = 20


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', IsInRecipesFilter)

    def get_queryset(self, request):
        ingredients = super().get_queryset(request)
        return ingredients.annotate(recipe_count=Count(
            'recipe_ingredients__recipe', distinct=True))

    def recipe_count(self, ingredient):
        return ingredient.recipe_count
    recipe_count.short_description = 'Количество рецептов'


class IngredientRecipeInline(admin.TabularInline):
    model = IngredientRecipe
    min_num = 1
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cooking_time', 'author', 'favorite_count',
                    'get_products', 'get_image')
    search_fields = ('name', 'author__username')
    list_filter = ('author',)
    inlines = (IngredientRecipeInline,)

    @admin.display(description='В избранном')
    def favorite_count(self, recipe):
        return recipe.favorite_recipes.count()

    @admin.display(description='Изображение')
    @mark_safe
    def get_image(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="80" height="60">'
        return 'Нет изображения'

    @admin.display(description='Продукты')
    @mark_safe
    def get_products(self, recipe):
        return (
            'Нет продуктов' if not recipe.recipe_ingredients.exists() else
            ''.join([
                f'{r.ingredient.name} - '
                f'{r.amount} {r.ingredient.measurement_unit}'
                for r in recipe.recipe_ingredients.select_related('ingredient')
            ])
        )


class UserRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


admin.site.register([Favorite, ShoppingCart], UserRecipeAdmin)
