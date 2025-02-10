from django.core.validators import MinValueValidator
from django.db import models
from users.models import User


class Ingredient(models.Model):
    """Модель ингредиента."""
    name = models.CharField(
        unique=True,
        max_length=128,
        verbose_name='Название',
        help_text='Укажите название'
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения',
        help_text='Укажите единицу измерения'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [models.UniqueConstraint(
            fields=['name', 'measurement_unit'],
            name='unique_name_measurement_unit'
        )]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
        help_text='Укажите автора рецепта'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name="Список ингредиентов"
    )
    name = models.CharField(
        max_length=256,
        verbose_name='Название рецепта',
        help_text='Укажите название рецепта'
    )
    image = models.ImageField(
        null=True,
        default=None,
        help_text="Картинка, закодированная в формате Base64.",
        verbose_name="Изображение",
        upload_to='recipes_images'
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Укажите описание рецепта'
    )
    cooking_time = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Время приготовления (в минутах)",
        help_text='Укажите время приготовления, от 1 мин'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Модель, связывающая ингредиент с рецептом."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipeingredients',
        verbose_name='Название рецепта',
        help_text='Укажите название рецепта'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipeingredients',
        verbose_name='Ингредиент рецепта',
        help_text='Укажите ингредиент рецепта'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Кол-во ингредиента',
        help_text='Укажите кол-во ингредиента, от 1 и более'
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Ингредиент - рецепта'
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(
            fields=['recipe', 'ingredient'],
            name='unique_recipe_ingredients'
        )]

    def __str__(self):
        return (f'{self.recipe}: {self.ingredient} - {self.amount} '
                f'{self.ingredient.measurement_unit}')


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_user_recipe_%(class)s"
            )
        ]
        ordering = ("-user",)

    def __str__(self):
        return f"{self.user} {self.recipe}"


class FavoriteRecipe(UserRecipeRelation):

    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        default_related_name = "favorites"


class ShoppingCart(UserRecipeRelation):

    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        default_related_name = "shopping_carts"
