from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportActionModelAdmin
from django.utils.safestring import mark_safe
from users.models import Subscribers, User

from .models import (Ingredient, Recipe, RecipeIngredient,
                     FavoriteRecipe, ShoppingCart)


class SubscribersInline(admin.TabularInline):
    """Настройка отображения подписчиков на автора рецептов и наоборот."""
    model = Subscribers
    min_num = 1


class AdminUser(UserAdmin):
    """Настройка Админки-Пользователей."""

    @admin.display(description='Подписчики')
    def get_subscribers(self, obj):
        """Функция для корректного отображения подписчиков."""
        return obj.authors.count()

    @admin.display(description='Рецепты')
    def get_recipes_count(self, obj):
        """Количество рецептов пользователя."""
        return obj.recipes.count()

    @admin.display(description='Подписки')
    def get_subscriptions_count(self, obj):
        """Количество подписок пользователя."""
        return obj.subscribers.count()

    @mark_safe
    def get_avatar(self, obj):
        """Метод для отображения аватара пользователя в админке."""
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" style="width: 50px; ' \
                'height: 50px;" />'
        return 'Нет аватара'

    list_display = (
        'id',
        'username',
        'first_name',
        'last_name',
        'email',
        'get_avatar',
        'get_recipes_count',
        'get_subscriptions_count',
        'get_subscribers',
    )
    list_filter = ('username',)
    search_fields = ('username',)
    ordering = ('username',)


class IngredientAdmin(ImportExportActionModelAdmin, admin.ModelAdmin):
    """Настройка Админки-Ингредиентов."""

    @admin.display(description='Число рецептов')
    def get_recipes_count(self, obj):
        """Количество рецептов, использующих данный ингредиент."""
        return obj.recipeingredients.count()

    list_display = (
        'id',
        'name',
        'measurement_unit',
        'get_recipes_count',
    )
    list_filter = ('measurement_unit',)
    search_fields = ('name', 'measurement_unit')
    ordering = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    """Настройка отображения ингредиентов в рецепте."""
    model = RecipeIngredient
    min_num = 1


class RecipeAdmin(admin.ModelAdmin):
    """Настройка Админки-Рецептов."""

    @mark_safe
    def get_image(self, obj):
        """Метод для отображения картинки рецепта в админке."""
        if obj.image:
            return f'<img src="{obj.image.url}" style="width: 100px; height: 100px;" />'
        return 'Нет изображения'

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        """Функция для корректного отображения ингредиентов в list_display Админке-Рецептов."""
        return '\n'.join(
            f'{ingredient.ingredient} - {ingredient.amount} {ingredient.ingredient.measurement_unit}'
            for ingredient in obj.recipeingredients.all()
        )

    @admin.display(description='Избранное')
    def get_favorites_count(self, obj):
        """Количество раз, когда рецепт добавлялся в избранное."""
        return obj.favorites.count()

    list_display = (
        'id',
        'name',
        'cooking_time',
        'author',
        'get_favorites_count',
        'get_ingredients',
        'get_image',
    )
    search_fields = ('name', 'author__username')
    list_filter = ('author', 'cooking_time')
    empty_value_display = 'Не задано'


admin.site.register(User, AdminUser)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Subscribers)
admin.site.register(FavoriteRecipe)
admin.site.register(ShoppingCart)
