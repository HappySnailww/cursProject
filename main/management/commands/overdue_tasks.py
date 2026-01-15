from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Task


class Command(BaseCommand):
    help = 'Показывает все просроченные задачи'

    def handle(self, *args, **options):
        now = timezone.now()

        overdue_tasks = Task.objects.filter(
            due_date__lt=now,
            status__in=['pending', 'in_progress']
        )

        if not overdue_tasks.exists():
            self.stdout.write(self.style.SUCCESS('Просроченных задач нет'))
            return

        self.stdout.write(self.style.WARNING('Просроченные задачи:'))

        for task in overdue_tasks:
            self.stdout.write(
                f'- {task.title} | пользователь: {task.user.username} | срок: {task.due_date.strftime("%d-%m-%Y %H:%M")}'
            )
