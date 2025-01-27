import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from recipes.models import (
    Recipe, Ingredient, RecipeIngredient, ShoppingCart, FavoriteRecipe
)
from users.models import Subscribers, User


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request')
        return bool(user and user.user.is_authenticated and Subscribers.objects.filter(author=obj, user=user.user).exists())

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError("Поле 'avatar' обязательно.")
        if not self.is_valid_avatar(value):
            raise serializers.ValidationError("Некорректные данные аватара.")
        return value

    def is_valid_avatar(self, avatar_data):
        # Здесь можно добавить логику валидации аватара
        return True

    def get_avatar(self, obj):
        return obj.avatar_url


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )

    def validate(self, data):
        self.check_user_exists(data['email'], data['username'])
        return data

    def check_user_exists(self, email, username):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.')
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует.')

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиента."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsInRecipeSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор для отображения ингредиентов рецепта."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецепта."""
    author = UserSerializer(read_only=True)
    image = Base64ImageField(required=True)
    ingredients = IngredientsInRecipeSerializer(many=True, write_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return FavoriteRecipe.objects.filter(user=request.user, recipe=obj).exists()
        return False  # Возвращаем False для неавторизованных пользователей

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()
        return False  # Возвращаем False для неавторизованных пользователей

    def validate(self, data):
        ingredients = data.get('ingredients')
        image = data.get('image')
        if not ingredients:
            raise serializers.ValidationError(
                'Укажите необходимые ингрeдиенты для рецепта!')

        ingredients_id_list = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_id_list) != len(set(ingredients_id_list)):
            raise serializers.ValidationError(
                'Вы указали одинаковые ингредиенты при создании рецепта!')

        if not image:
            raise serializers.ValidationError(
                'Вы не указали картинку рецепта!')

        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self.add_ingredients(ingredients, recipe)
        return recipe

    def update(self, recipe, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe.ingredients.clear()
        recipe = super().update(recipe, validated_data)
        self.add_ingredients(ingredients, recipe)
        return recipe

    def add_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = instance.image.url if instance.image else None

        ingredients = instance.recipeingredients.select_related('ingredient')
        representation['ingredients'] = [
            {
                'id': ingredient.ingredient.id,
                'name': ingredient.ingredient.name,
                'measurement_unit': ingredient.ingredient.measurement_unit,
                'amount': ingredient.amount
            }
            for ingredient in ingredients
        ]
        return representation


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения краткой информации о рецепте."""
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    name = serializers.ReadOnlyField(
        source='recipe.name',
        read_only=True)
    image = serializers.ImageField(
        source='recipe.image',
        read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time',
        read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsListSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения подписок для текущего пользователя."""
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscribers
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_avatar(self, obj):
        return obj.author.avatar_url

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return Subscribers.objects.filter(
            author=obj.author, user=user).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit', 6)
        try:
            limit = int(limit)
        except ValueError:
            limit = 6
        return RecipeMinifiedSerializer(
            Recipe.objects.filter(author=obj.author)[:limit], many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""

    class Meta:
        model = Subscribers
        fields = '__all__'

    def validate(self, data):
        if data['author'] == data['user']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!')
        if Subscribers.objects.filter(author=data['author'],
                                      user=data['user']).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора!')
        return data

    def to_representation(self, author):
        return SubscriptionsListSerializer(author, context=self.context).data
