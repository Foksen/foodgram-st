from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='short_link',
            field=models.SlugField(blank=True, max_length=64, null=True, unique=True, verbose_name='Короткая ссылка'),
        ),
    ] 