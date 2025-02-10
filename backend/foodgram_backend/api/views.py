import os

from django.db.models import Exists, F, OuterRef, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from djoser.views import UserViewSet
from recipes.models import FavoriteRecipe, Ingredient, Recipe, ShoppingCart
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import Subscribers, User

from . import serializers
from .paginations import Pagination
from .permissions import IsAuthorOrReadOnly


class BaseFilterViewSet(viewsets.ModelViewSet):
    """Вспомогательный вьюсет для работы фильтрации."""
    pagination_class = Pagination

    def filter_queryset(self, queryset):
        request = self.request
        filters = {
            'is_favorited': request.query_params.get('is_favorited'),
            'is_in_shopping_cart': request.query_params.get(
                'is_in_shopping_cart'
            ),
            'author_id': request.query_params.get('author')
        }

        if request.user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(FavoriteRecipe.objects.filter(
                    user=request.user, recipe=OuterRef('pk'))),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    user=request.user, recipe=OuterRef('pk')))
            )

            if filters['is_favorited'] in ['0', '1']:
                queryset = queryset.filter(
                    is_favorited=(filters['is_favorited'] == '1')
                )

            if filters['is_in_shopping_cart'] in ['0', '1']:
                queryset = queryset.filter(
                    is_in_shopping_cart=(filters['is_in_shopping_cart'] == '1')
                )

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


class CustomUserViewSet(UserViewSet):
    """Вьюсет для пользователей."""
    queryset = User.objects.all()
    serializer_class = serializers.CustomUserSerializer
    pagination_class = Pagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(methods=['GET'], detail=False)
    def subscriptions(self, request):
        subscriptions = Subscribers.objects.filter(user=request.user)
        page = self.paginate_queryset(subscriptions)
        serializer = serializers.SubscriptionSerializer(
            [sub.author for sub in page],
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST', 'DELETE'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated],
            url_path=r'(?P<id>\d+)/subscribe')
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Subscribers.objects.filter(author=author,
                                          user=request.user).exists():
                return Response({'error': 'Вы уже подписаны на этого автора!'},
                                status=status.HTTP_400_BAD_REQUEST)

            Subscribers.objects.create(author=author, user=request.user)
            return Response(
                serializers.SubscriptionSerializer(
                    author, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            subscription = Subscribers.objects.filter(author=author,
                                                      user=request.user
                                                      ).first()
            if not subscription:
                return Response(
                    {'error': 'Подписка не найдена.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        user = request.user
        serializer = serializers.CustomUserSerializer(
            user, context={'request': request}
        )
        return Response(serializer.data)

    @action(methods=['PUT', 'DELETE'], detail=False, url_path='me/avatar')
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            data = request.data
            if 'avatar' not in data:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(user, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'avatar': serializer.data['avatar']},
                            status=status.HTTP_200_OK)

        if request.method == 'DELETE':
            if user.avatar and os.path.isfile(user.avatar.path):
                os.remove(user.avatar.path)
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(BaseFilterViewSet):
    """Вьюсет для рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = serializers.RecipeSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.RecipeListSerializer
        return serializers.RecipeSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        instance = self.get_object()

        url = f"{request.get_host()}/recipes/{instance.id}"

        return Response(data={"short-link": url})

    @action(methods=['GET'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        shoppingcart = ShoppingCart.objects.filter(user=request.user).values(
            'recipe_id__ingredients__name'
        ).annotate(
            amount=Sum('recipe_id__recipeingredients__amount'),
            measurement_unit=F('recipe_id__ingredients__measurement_unit')
        )

        ingredients = self.aggregate_ingredients(shoppingcart)
        recipes = ShoppingCart.objects.filter(user=request.user).values_list(
            'recipe_id__name', flat=True).distinct()

        report_date = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        report_content = '\n'.join([
            f'Список покупок на дату {report_date}:',
            'Продукты:',
            *[
                f"{idx + 1}. {ingredient.capitalize()} - {amount} "
                f"({measurement_unit})"
                for idx, (ingredient, (amount, measurement_unit))
                in enumerate(ingredients.items())
            ],
            'Рецепты:',
            *[f"{recipe}" for recipe in recipes],
        ])

        return Response(report_content, content_type='text/plain')

    def aggregate_ingredients(self, shoppingcart):
        ingredients = {}
        for ingredient in shoppingcart:
            ingredient_name = ingredient['recipe_id__ingredients__name']
            amount = ingredient['amount']
            measurement_unit = ingredient['measurement_unit']
            ingredients[ingredient_name] = (
                ingredients.get(
                    ingredient_name, (0, measurement_unit))[0] + amount,
                measurement_unit
            )

        return ingredients

    @action(methods=['POST', 'DELETE'],
            detail=False,
            permission_classes=[permissions.IsAuthenticated],
            url_path=r'(?P<id>\d+)/shopping_cart')
    def shopping_cart(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        return self.update_cart(request, recipe)

    @staticmethod
    def update_cart(request, recipe):
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже добавлен!'},
                                status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            recipe.is_in_shopping_cart = True
            recipe.save()

            serializer = serializers.RecipeMinifiedSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        shopping_cart_item = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe).first()
        if not shopping_cart_item:
            return Response({'errors': 'Рецепт не найден в корзине.'},
                            status=status.HTTP_400_BAD_REQUEST)

        shopping_cart_item.delete()
        recipe.is_in_shopping_cart = False
        recipe.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST', 'DELETE'],
            detail=True,
            permission_classes=[permissions.IsAuthenticated],
            url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.update_favorite(request, recipe)

    @staticmethod
    def update_favorite(request, recipe):
        if request.method == 'POST':
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

        favorite_recipe = request.user.favorites.filter(recipe=recipe)
        if not favorite_recipe.exists():
            return Response({'errors': 'Рецепт не найден в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)

        favorite_recipe.delete()
        recipe.is_favorited = False
        recipe.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
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
