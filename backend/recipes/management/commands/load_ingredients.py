import json
import os
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает продукты'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Путь к файлу с продуктами (дефолт - data/ingredients.json)'
        )

    def handle(self, *args, **options):
        try:
            file_path = options.get('path') or '/app/data/ingredients.json'

            if not os.path.exists(file_path):
                self.stderr.write(self.style.ERROR(
                    f'Файл {file_path} не найден!'))
                return

            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)

            ingredients_to_create = []
            existing_ingredients = set(
                Ingredient.objects.values_list('name', 'measurement_unit')
            )

            for ingredient in ingredients_data:
                name = ingredient.get('name')
                measurement_unit = ingredient.get('measurement_unit')

                if not name or not measurement_unit:
                    continue

                if (name, measurement_unit) not in existing_ingredients:
                    ingredients_to_create.append(
                        Ingredient(
                            name=name,
                            measurement_unit=measurement_unit
                        )
                    )

            if ingredients_to_create:
                Ingredient.objects.bulk_create(ingredients_to_create)

            self.stdout.write(self.style.SUCCESS('Продукты успешно загружены'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Ошибка при работе с файлом {file_path}: {str(e)}'))
