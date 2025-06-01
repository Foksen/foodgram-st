from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart,
    User, Subscription
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name')
    list_filter = ('username', 'email')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 20
    ordering = ('username',)
    fieldsets = (
        ('Основное', {
            'fields': ('username', 'email', 'password')
        }),
        ('Имя и фамилия', {
            'fields': ('first_name', 'last_name')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Даты', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    readonly_fields = ('last_login', 'date_joined')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'author')
    search_fields = ('subscriber__username', 'author__username')
    list_filter = ('author', 'subscriber')
    list_per_page = 20


class IsInRecipesFilter(admin.SimpleListFilter):
    title = 'В рецептах'
    parameter_name = 'is_in_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(ingredient_recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(ingredient_recipes__isnull=True)
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', IsInRecipesFilter)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(recipe_count=Count(
            'ingredient_recipes__recipe', distinct=True))

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

    @mark_safe
    def get_image(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="80" height="60">'
        return 'Нет изображения'
    get_image.short_description = 'Изображение'

    @mark_safe
    def get_products(self, recipe):
        ingredients = recipe.recipe_ingredients.select_related('ingredient')
        result = []
        for item in ingredients:
            result.append(
                f'{item.ingredient.name} - {item.amount} '
                f'{item.ingredient.measurement_unit}'
            )
        return '<br>'.join(result) if result else 'Нет продуктов'
    get_products.short_description = 'Продукты'


class UserRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


admin.site.register([Favorite, ShoppingCart], UserRecipeAdmin)
