import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from JSON file'

    def handle(self, *args, **kwargs):
        with open('D:/Dev/foodgram-st/data/ingredients.json', 'r',
                  encoding='utf-8') as file:
            ingredients = json.load(file)
            for ingredient in ingredients:
                name = ingredient['name']
                measurement_unit = ingredient['measurement_unit']
                Ingredient.objects.get_or_create(
                    name=name,
                    measurement_unit=measurement_unit
                )
        self.stdout.write(self.style.SUCCESS('Ingredients loaded successfully'))
