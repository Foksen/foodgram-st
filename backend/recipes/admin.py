from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart,
    User, Subscription
)


class HasRecipesFilter(admin.SimpleListFilter):
    title = 'есть рецепты'
    parameter_name = 'has_recipes'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.annotate(recipe_count=Count('recipes')).filter(recipe_count__gt=0)
        if self.value() == 'no':
            return queryset.annotate(recipe_count=Count('recipes')).filter(recipe_count=0)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.annotate(subscr_count=Count('author')).filter(subscr_count__gt=0)
        if self.value() == 'no':
            return queryset.annotate(subscr_count=Count('author')).filter(subscr_count=0)
        return queryset


class HasSubscribersFilter(admin.SimpleListFilter):
    title = 'есть подписчики'
    parameter_name = 'has_subscribers'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.annotate(subs_count=Count('subscribers')).filter(subs_count__gt=0)
        if self.value() == 'no':
            return queryset.annotate(subs_count=Count('subscribers')).filter(subs_count=0)
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'get_full_name', 'email', 'get_avatar', 
                   'get_recipe_count', 'get_subscription_count', 'get_subscriber_count')
    list_filter = (HasRecipesFilter, HasSubscriptionsFilter, HasSubscribersFilter, 
                  'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    list_per_page = 20
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'avatar')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['get_avatar']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            recipe_count=Count('recipes', distinct=True),
            subscription_count=Count('author', distinct=True),
            subscriber_count=Count('subscribers', distinct=True)
        )
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'ФИО'
    
    @mark_safe
    def get_avatar(self, obj):
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="80" height="80" />'
        return 'Нет аватара'
    get_avatar.short_description = 'Аватар'
    
    def get_recipe_count(self, obj):
        return obj.recipe_count
    get_recipe_count.short_description = 'Количество рецептов'
    
    def get_subscription_count(self, obj):
        return obj.subscription_count
    get_subscription_count.short_description = 'Подписок'
    
    def get_subscriber_count(self, obj):
        return obj.subscriber_count
    get_subscriber_count.short_description = 'Подписчиков'


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
