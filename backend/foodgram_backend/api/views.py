from django.db.models import F, Exists, OuterRef
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from recipes.models import Recipe, Ingredient, FavoriteRecipe, ShoppingCart
from users.models import Subscribers, User
from .paginations import Pagination
from . import serializers


class BaseFilterViewSet(viewsets.ModelViewSet):
    """Вспомогательный вьюсет для работы фильтрации."""
    pagination_class = Pagination

    def filter_queryset(self, queryset):
        request = self.request
        filters = {
            'is_favorited': request.query_params.get('is_favorited'),
            'is_in_shopping_cart': request.query_params.get('is_in_shopping_cart'),
            'author_id': request.query_params.get('author')
        }

        if request.user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(FavoriteRecipe.objects.filter(user=request.user, recipe=OuterRef('pk'))),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(user=request.user, recipe=OuterRef('pk')))
            )

            if filters['is_favorited'] in ['0', '1']:
                queryset = queryset.filter(is_favorited=(filters['is_favorited'] == '1'))

            if filters['is_in_shopping_cart'] in ['0', '1']:
                queryset = queryset.filter(is_in_shopping_cart=(filters['is_in_shopping_cart'] == '1'))

        if filters['author_id']:
            queryset = queryset.filter(author_id=filters['author_id'])

        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.filter_queryset(queryset)

    def get_paginated_response_data(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(queryset, many=True).data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return self.get_paginated_response_data(queryset)


class UserViewSet(BaseFilterViewSet):
    """Вьюсет для пользователей."""
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = serializers.UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['GET'], detail=False)
    def subscriptions(self, request):
        subscriptions = Subscribers.objects.filter(user=request.user)
        page = self.paginate_queryset(subscriptions)
        serializer = serializers.SubscriptionsListSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST', 'DELETE'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated, ],
            url_path=r'(?P<id>\d+)/subscribe')
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        data = {'author': author.id,
                'user': request.user.id}
        if request.method == 'POST':
            serializer = serializers.SubscribeSerializer(
                data=data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            subscription, _ = Subscribers.objects.filter(
                author=author.id,
                user=request.user.id).delete()
            if subscription:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        user = request.user
        serializer = serializers.UserSerializer(
            user, context={'request': request}
        )
        return Response(serializer.data)

    @action(methods=['PUT', 'DELETE'], detail=False, url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            return self.update_avatar(user, request.data)
        return self.delete_avatar(user)

    def update_avatar(self, user, data):
        if 'avatar' not in data:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': serializer.data['avatar']},
                        status=status.HTTP_200_OK)

    def delete_avatar(self, user):
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=False, url_path='set_password')
    def set_password(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not user.check_password(current_password):
            return Response({'detail': 'Неверный текущий пароль.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not new_password:
            return Response({'new_password': ['Это поле обязательно.']},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(BaseFilterViewSet):
    """Вьюсет для рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = serializers.RecipeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_link']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('-id')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = f"http://localhost:8000/recipes/{recipe.id}/"
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(methods=['GET'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        shoppingcart = ShoppingCart.objects.filter(user=request.user).values(
            'recipe_id__ingredients__name'
        ).annotate(
            amount=F('recipe_id__recipeingredients__amount'),
            measurement_unit=F('recipe_id__ingredients__measurement_unit')
        ).order_by('recipe_id__ingredients__name')

        ingredients = self.aggregate_ingredients(shoppingcart)
        return self.create_shopping_cart_file(ingredients)

    def aggregate_ingredients(self, shoppingcart):
        ingredients = {}
        for ingredient in shoppingcart:
            ingredient_name = ingredient['recipe_id__ingredients__name']
            amount = ingredient['amount']
            measurement_unit = ingredient['measurement_unit']
            if ingredient_name not in ingredients:
                ingredients[ingredient_name] = (amount, measurement_unit)
            else:
                ingredients[ingredient_name] = (
                    ingredients[ingredient_name][0] + amount,
                    measurement_unit
                )
        return ingredients

    def create_shopping_cart_file(self, ingredients):
        with open("shopping_cart.txt", "w") as file:
            file.write('Ваш список покупок:\n')
            for ingredient, (amount, measurement_unit) in ingredients.items():
                file.write(f'{ingredient} - {amount} ({measurement_unit}).\n')
        return FileResponse(open('shopping_cart.txt', 'rb'))

    @action(methods=['POST', 'DELETE'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated],
            url_path=r'(?P<id>\d+)/shopping_cart')
    def shopping_cart(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        if request.method == 'POST':
            return self.add_to_shopping_cart(recipe)
        return self.remove_from_shopping_cart(recipe)

    def add_to_shopping_cart(self, recipe):
        if ShoppingCart.objects.filter(user=self.request.user,
                                       recipe=recipe).exists():
            return Response({'errors': 'Рецепт уже добавлен!'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = serializers.ShoppingCartSerializer(data={})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user, recipe=recipe)
        recipe.is_in_shopping_cart = True
        recipe.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_shopping_cart(self, recipe):
        shoppingcart_status, _ = ShoppingCart.objects.filter(
            user=self.request.user, recipe=recipe).delete()
        if shoppingcart_status:
            recipe.is_in_shopping_cart = False
            recipe.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': 'Рецепт не найден в списке покупок.'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', 'DELETE'],
            detail=True,
            permission_classes=[permissions.IsAuthenticated],
            url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            return self.add_to_favorites(request, recipe)
        return self.remove_from_favorites(request, recipe)

    def add_to_favorites(self, request, recipe):
        if request.user.favorites.filter(recipe=recipe).exists():
            return Response({'errors': 'Рецепт уже добавлен в избранное!'},
                            status=status.HTTP_400_BAD_REQUEST)

        FavoriteRecipe.objects.create(user=request.user, recipe=recipe)
        recipe.is_favorited = True
        recipe.save()

        serializer = serializers.RecipeMinifiedSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorites(self, request, recipe):
        favorite_recipe = request.user.favorites.filter(recipe=recipe)
        if not favorite_recipe.exists():
            return Response({'errors': 'Рецепт не найден в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)

        favorite_recipe.delete()
        recipe.is_favorited = False
        recipe.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
    pagination_class = None
    permission_classes = (permissions.AllowAny,)
    http_method_names = ['get', ]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset
