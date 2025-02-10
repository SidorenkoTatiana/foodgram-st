from djoser.serializers import UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes import models
from rest_framework import serializers
from users.models import Subscribers, User


class CustomUserSerializer(UserCreateSerializer):
    """Сериализатор для пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, user_instance):
        user = self.context.get('request')
        return (user and user.user.is_authenticated
                and Subscribers.objects.filter(
                    author=user_instance,
                    user=user.user).exists())

    def validate(self, data):
        avatar = self.initial_data.get("avatar")
        if not avatar:
            raise serializers.ValidationError("Аватар не может быть пустым")

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиента."""

    class Meta:
        model = models.Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientResipeSerializer(serializers.ModelSerializer):
    """Вспомогательный cериалайзер для корректного отображения
       Ингредиентов - рецепта."""
    id = serializers.ReadOnlyField(
        source='ingredient.id')
    name = serializers.ReadOnlyField(
        source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = models.RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientsInRecipeSerializer(serializers.ModelSerializer):
    """Вспомогательный cериалайзер для корректного добавления
       Ингредиентов в рецепт при его создании."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=models.Ingredient.objects.all())

    class Meta:
        model = models.RecipeIngredient
        fields = ('id', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для рецепта."""

    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField(required=True)
    ingredients = IngredientResipeSerializer(many=True,
                                             source='recipeingredients',
                                             read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = models.Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        extra_kwargs = {
            'cooking_time': {'min_value': 1}
        }

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (request.user.is_authenticated
                and models.FavoriteRecipe.objects.filter(
                    user=request.user,
                    recipe=obj
                ).exists()
                )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (request.user.is_authenticated
                and models.ShoppingCart.objects.filter(
                    user=request.user,
                    recipe=obj
                ).exists()
                )


class RecipeSerializer(serializers.ModelSerializer):
    """Cериалайзер для метода Post, PATCH и DEL модели рецептов."""

    ingredients = IngredientsInRecipeSerializer(many=True, write_only=True)
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    image = Base64ImageField()

    class Meta:
        model = models.Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "name",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def validate(self, data):
        """Валидация при создании рецепта."""
        ingredients = data.get('ingredients')
        image = data.get('image')
        if not ingredients:
            raise serializers.ValidationError('Укажите необходимые'
                                              ' ингридиенты для рецепта!')
        ingredients_id_list = [id['id'] for id in ingredients]
        if len(ingredients_id_list) != len(set(ingredients_id_list)):
            raise serializers.ValidationError('Вы указали одинаковые '
                                              'ингридиенты при создании '
                                              'рецепта!')
        if not image:
            raise serializers.ValidationError('Вы не указали картинку '
                                              'рецепта!')
        return data

    def create(self, validated_data):

        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self.add_ingredients(ingredients, recipe)
        return recipe

    def update(self, recipe, validated_data):

        ingredients = validated_data.pop('ingredients')
        recipe.ingredients.clear()
        self.add_ingredients(ingredients, recipe)
        return super().update(recipe, validated_data)

    def add_ingredients(self, ingredients, recipe):
        recipe_ingredients = [
            models.RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount'])
            for ingredient in ingredients
        ]
        models.RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def to_representation(self, instance):
        serializer = RecipeListSerializer(
            instance, context={"request": self.context.get("request")}
        )
        return serializer.data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения краткой информации о рецепте."""

    class Meta:
        model = models.Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class SubscriptionSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField(method_name="get_recipes")
    recipes_count = serializers.ReadOnlyField(source="recipes.count")

    class Meta:
        model = User
        fields = CustomUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get("recipes_limit")

        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass

        return RecipeMinifiedSerializer(
            recipes, context={"request": request}, many=True
        ).data
