import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты'

    def handle(self, *args, **options):
        file_path = os.path.join(
            os.path.dirname(settings.BASE_DIR), 'data', 'ingredients.csv'
        )

        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден!')
            )
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) != 2:
                        continue
                    name, measurement_unit = row
                    Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )

            self.stdout.write(
                self.style.SUCCESS('Ингредиенты загружены')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ингредиенты не удалось загрузить: {e}')
            )
