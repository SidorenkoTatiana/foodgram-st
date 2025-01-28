from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportActionModelAdmin

from users.models import Subscribers, User

from .models import Ingredient, Recipe, RecipeIngredient


class SubscribersInline(admin.TabularInline):
    """Настройка отображения подписчиков на автора рецептов и наоборот."""
    model = Subscribers
    min_num = 1


class AdminUser(UserAdmin):
    """Настройка Админки-Пользователей."""

    @admin.display(description='Подписчики')
    def get_subscribers(self, obj):
        """Функция для корректного отображения подписчиков в
           list_display Админке-Пользователей."""
        subscribers = Subscribers.objects.filter(author_id=obj.id)
        return [i.user for i in subscribers]

    list_display = (
        'id',
        'username',
        'first_name',
        'last_name',
        'email',
        'get_subscribers',
    )
    list_filter = ('username',)
    search_fields = ('username',)
    ordering = ('username',)


class IngredientAdmin(ImportExportActionModelAdmin, admin.ModelAdmin):
    """Настройка Админки-Ингредиентов + добавление возможности импорта/экспорта
    данных из CSV-файлов в БД из Админки."""
    list_display = (
        'id',
        'name',
        'measurement_unit',
    )
    list_filter = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    """Настройка отображения ингредиентов в рецепте."""
    model = RecipeIngredient
    min_num = 1


class RecipeAdmin(admin.ModelAdmin):
    """Настройка Админки-Рецептов."""

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        """Функция для корректного отображения ингредиентов в list_display
           Админке-Рецептов."""
        ingredients = obj.recipeingredients.all()
        return (
            ', '.join(
                [f'{ingredient.ingredient} - {ingredient.amount} '
                 f'{ingredient.ingredient.measurement_unit}'
                 for ingredient in ingredients])
        )

    list_display = (
        'id',
        'name',
        'author',
        'get_ingredients',
    )
    search_fields = ('name',)
    list_filter = ('name',)
    empty_value_display = 'Не задано'


admin.site.register(User, AdminUser)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
