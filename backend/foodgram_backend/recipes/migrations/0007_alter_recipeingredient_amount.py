# Generated by Django 5.1.4 on 2025-01-12 17:13

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_alter_ingredient_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipeingredient',
            name='amount',
            field=models.PositiveSmallIntegerField(help_text='Укажите кол-во ингредиента, от 1 и более', validators=[django.core.validators.MinValueValidator(1)], verbose_name='Кол-во ингредиента'),
        ),
    ]
