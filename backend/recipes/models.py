from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator
from django.db import models
import re
from django.core.exceptions import ValidationError


def validate_username(value):
    if not re.match(r'^[\w.@+-]+$', value):
        raise ValidationError(
            'Имя пользователя содержит недопустимые символы'
        )
    return value


class User(AbstractUser):
    email = models.EmailField('Электронная почта', unique=True)
    username = models.CharField(
        'Ник',
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
    )
    first_name = models.CharField(
        'Имя',
        max_length=150,
        blank=False,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        blank=False,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        swappable = 'AUTH_USER_MODEL'
        db_table = 'recipes_user'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='author',
    )
    subscriber = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='subscribers',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'subscriber'],
                name='unique_subscription'
            ),
        ]

    def __str__(self):
        return f'{self.subscriber} подписан на {self.author}'


class Ingredient(models.Model):
    name = models.CharField(
        'Название',
        max_length=128,
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=64,
    )

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    name = models.CharField('Название', max_length=256)
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/images/',
    )
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Продукты',
    )
    cooking_time = models.PositiveBigIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(1)]
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Продукт',
        related_name='ingredient_recipes'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Продукт в рецепте'
        verbose_name_plural = 'Продукты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredient_recipe'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} ({self.ingredient.measurement_unit}) - '
            f'{self.amount}'
        )


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(app_label)s_%(class)s_unique'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class Favorite(UserRecipeRelation):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Рецепт'
    )

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        default_related_name = 'favorites'


class ShoppingCart(UserRecipeRelation):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Рецепт'
    )

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        default_related_name = 'shopping_carts'
