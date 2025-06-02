import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction

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
            batch_size = 1000

            if not os.path.exists(file_path):
                self.stderr.write(self.style.ERROR(
                    f'Файл {file_path} не найден!'))
                return

            with open(file_path, 'r', encoding='utf-8') as file:
                ingredients_data = json.load(file)

            existing_names_units = set(
                Ingredient.objects.values_list('name', 'measurement_unit')
            )
            
            total_ingredients = len(ingredients_data)
            created_count = 0
            skipped_count = 0
            batch_count = 0
            
            with transaction.atomic():
                ingredient_batch = []
                
                for ingredient in ingredients_data:
                    name = ingredient.get('name')
                    measurement_unit = ingredient.get('measurement_unit')

                    if not name or not measurement_unit:
                        skipped_count += 1
                        continue

                    if (name, measurement_unit) not in existing_names_units:
                        ingredient_batch.append(
                            Ingredient(
                                name=name,
                                measurement_unit=measurement_unit
                            )
                        )
                        created_count += 1
                    else:
                        skipped_count += 1
                        
                    if len(ingredient_batch) >= batch_size:
                        Ingredient.objects.bulk_create(ingredient_batch)
                        batch_count += 1
                        self.stdout.write(
                            f'Обработано {batch_count} батчей, '
                            f'всего {batch_count * batch_size} ингредиентов'
                        )
                        ingredient_batch = []
                
                if ingredient_batch:
                    Ingredient.objects.bulk_create(ingredient_batch)
                    batch_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Загрузка завершена: '
                    f'создано {created_count}, пропущено {skipped_count}'
                )
            )

        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Ошибка при работе с файлом {file_path}: {str(e)}'))
