from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords

class Category(models.Model):
    COLOR_CHOICES = [
        ('#FF0000', 'Красный'),
        ('#00FF00', 'Зеленый'),
        ('#FFFF00', 'Желтый'),
        ('#0000FF', 'Синий'),
        ('#FFA500', 'Оранжевый'),
        ('#800080', 'Фиолетовый'),
        ('#FFC0CB', 'Розовый'),
        ('#A52A2A', 'Коричневый'),
        ('#808080', 'Серый'),
        ('#FFFFFF', 'Белый'),
    ]

    title = models.CharField('Название', max_length=50)
    color = models.CharField(
        'Цвет',
        max_length=7,
        choices=COLOR_CHOICES,
        default='#FFFFFF'
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        unique_together = ['title']


class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('in_progress', 'В процессе'),
        ('completed', 'Выполнено'),
    ]
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Критический'),
    ]

    title = models.CharField('Название', max_length=50)
    description = models.TextField('Описание')
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    priority = models.PositiveIntegerField(
        'Приоритет',
        choices=PRIORITY_CHOICES,
        default=2
    )
    due_date = models.DateTimeField('Срок выполнения')
    creation_date = models.DateTimeField('Дата создания')
    update_date = models.DateTimeField('Дата обновления')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        verbose_name='Категория',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='tasks',
        help_text='Пользователь, создавший задачу'
    )

    history = HistoricalRecords()

    def get_comments_preview(self, limit=5):
        comments = self.comments.all()[:limit]
        if comments:
            result = []
            for comment in comments:
                result.append(f"{comment.user.username}: {comment.text[:50]}...")
            return "\n".join(result)
        return "Нет комментариев"

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.creation_date = timezone.now()
        self.update_date = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'


class Comment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        verbose_name='Задача',
        related_name='comments',
        help_text='Задача, к которой оставлен комментарий'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='task_comments',
        help_text='Пользователь, оставивший комментарий'
    )
    text = models.TextField(
        'Текст комментария',
        max_length=1000,
        help_text='Максимальная длина 1000 символов'
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True,
        help_text='Дата и время создания комментария'
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True,
        help_text='Дата и время последнего изменения комментария'
    )

    history = HistoricalRecords()

    def __str__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Комментарий от {self.user.username} к задаче '{self.task.title}': {preview}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.task.update_date = timezone.now()
            self.task.save(update_fields=['update_date'])
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]