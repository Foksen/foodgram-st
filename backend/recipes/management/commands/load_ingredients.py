import json
from django.core.management.base import BaseCommand

from recipes.models import Ingredient

# Думаю, лучше сделать константу, не понимаю почему "лишняя строка"
BATCH_SIZE = 1000


class Command(BaseCommand):
    help = "Загружает продукты"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Путь к файлу с продуктами (дефолт - data/ingredients.json)",
        )

    def handle(self, *args, **options):
        try:
            file_path = (
                options.get("path") or "/app/data/ingredients.json"
            )

            with open(file_path, "r", encoding="utf-8") as file:
                ingredients_data = json.load(file)
                total_count = 0

                for i in range(0, len(ingredients_data), BATCH_SIZE):
                    batch = ingredients_data[i:i + BATCH_SIZE]
                    ingredient_batch = [
                        Ingredient(**ingredient)
                        for ingredient in batch
                    ]

                    created = Ingredient.objects.bulk_create(
                        ingredient_batch,
                        ignore_conflicts=True
                    )
                    total_count += len(created)

            # Не понял что значит "замените на анализ ответа от bulk_create"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Загрузка завершена: "
                    f"считано {total_count} продуктов"
                )
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(
                    f"Ошибка при работе с файлом {file_path}: {str(e)}"
                )
            )
