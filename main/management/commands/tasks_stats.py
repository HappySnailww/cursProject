from django.core.management.base import BaseCommand

from main.models import Task


class Command(BaseCommand):
    help = "Показывает статистику задач по статусам"

    def handle(self, *args, **options):
        total = Task.objects.count()

        pending = Task.objects.filter(status="pending").count()
        in_progress = Task.objects.filter(status="in_progress").count()
        completed = Task.objects.filter(status="completed").count()

        self.stdout.write(self.style.SUCCESS("Статистика задач:"))
        self.stdout.write(f"Всего задач: {total}")
        self.stdout.write(f"В ожидании: {pending}")
        self.stdout.write(f"В процессе: {in_progress}")
        self.stdout.write(f"Завершено: {completed}")
