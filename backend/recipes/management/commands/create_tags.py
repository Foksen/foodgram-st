from django.core.management.base import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Создание тегов'

    def handle(self, *args, **options):
        tags = [
            {'name': 'Завтрак', 'color': '#E26C2D', 'slug': 'breakfast'},
            {'name': 'Обед', 'color': '#49B64E', 'slug': 'lunch'},
            {'name': 'Ужин', 'color': '#8775D2', 'slug': 'dinner'}
        ]

        for tag_data in tags:
            Tag.objects.get_or_create(
                name=tag_data['name'],
                color=tag_data['color'],
                slug=tag_data['slug']
            )

        self.stdout.write(
            self.style.SUCCESS('Теги созданы')
        )
