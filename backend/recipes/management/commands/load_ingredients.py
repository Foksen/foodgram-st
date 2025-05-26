import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты'

    def handle(self, *args, **options):
        possible_paths = [
            '/app/data/ingredients.csv',
            os.path.join(os.path.dirname(settings.BASE_DIR), 'data', 'ingredients.csv')
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break

        if file_path is None:
            self.stdout.write(
                self.style.ERROR('Файл ingredients.csv не найден!')
            )
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                count = 0
                for row in reader:
                    if len(row) != 2:
                        continue
                    name, measurement_unit = row
                    _, created = Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                    if created:
                        count += 1

            self.stdout.write(
                self.style.SUCCESS(f'Загружено {count} ингредиентов')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ингредиенты не удалось загрузить: {e}')
            )
