from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from __future__ import annotations

class Category(models.Model):
    """
    Категория задач.

    Используется для группировки задач по тематике
    и визуального выделения с помощью цвета.
    """
    COLOR_CHOICES = [
        ("#FF0000", "Красный"),
        ("#00FF00", "Зеленый"),
        ("#FFFF00", "Желтый"),
        ("#0000FF", "Синий"),
        ("#FFA500", "Оранжевый"),
        ("#800080", "Фиолетовый"),
        ("#FFC0CB", "Розовый"),
        ("#A52A2A", "Коричневый"),
        ("#808080", "Серый"),
        ("#FFFFFF", "Белый"),
    ]

    title = models.CharField("Название", max_length=50)
    color = models.CharField(
        "Цвет", max_length=7, choices=COLOR_CHOICES, default="#FFFFFF"
    )

    history = HistoricalRecords()

    def __str__(self) -> str:
        """
        Возвращает название категории.

        Returns:
            Название категории.
        """
        return self.title

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        unique_together = ["title"]


class Task(models.Model):
    """
    Модель задачи.

    Содержит информацию о названии, описании,
    статусе, приоритете, сроке выполнения,
    категории и владельцах задачи.
    """
    STATUS_CHOICES = [
        ("pending", "В ожидании"),
        ("in_progress", "В процессе"),
        ("completed", "Выполнено"),
    ]
    PRIORITY_CHOICES = [
        (1, "Низкий"),
        (2, "Средний"),
        (3, "Высокий"),
        (4, "Критический"),
    ]

    title = models.CharField("Название", max_length=50)
    description = models.TextField("Описание")
    status = models.CharField(
        "Статус", max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    priority = models.PositiveIntegerField(
        "Приоритет", choices=PRIORITY_CHOICES, default=2
    )
    due_date = models.DateTimeField("Срок выполнения")
    creation_date = models.DateTimeField("Дата создания", auto_now_add=True)
    update_date = models.DateTimeField("Дата обновления", auto_now=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        verbose_name="Категория",
        null=True,
        blank=True,
    )
    users = models.ManyToManyField(
        User,
        verbose_name="Владельцы задачи",
        related_name="tasks",
    )

    history = HistoricalRecords()

    def get_comments_preview(self, limit: int = 5) -> str:
        """
        Возвращает краткое представление комментариев задачи.

        Args:
            limit: Максимальное количество комментариев
                для отображения.

        Returns:
            Строка с краткой информацией о комментариях.
        """
        comments = self.comments.select_related("user").all()[:limit]

        if not comments:
            return "Нет комментариев"

        result: list[str] = []
        for comment in comments:
            result.append(f"{comment.user.username}: {comment.text[:50]}...")

        return "\n".join(result)

    def __str__(self) -> str:
        """
        Возвращает строковое представление задачи.

        Returns:
            Название задачи.
        """
        return f"{self.title} ({self.users})"

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"


class Comment(models.Model):
    """
    Комментарий к задаче.

    Хранит текст комментария, автора,
    связанную задачу и даты создания
    и обновления.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        verbose_name="Задача",
        related_name="comments",
        help_text="Задача, к которой оставлен комментарий",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор",
        related_name="task_comments",
        help_text="Пользователь, оставивший комментарий",
    )
    text = models.TextField(
        "Текст комментария",
        max_length=1000,
        help_text="Максимальная длина 1000 символов",
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
        help_text="Дата и время создания комментария",
    )
    updated_at = models.DateTimeField(
        "Дата обновления",
        auto_now=True,
        help_text="Дата и время последнего изменения комментария",
    )

    history = HistoricalRecords()

    def __str__(self) -> str:
        """
        Возвращает краткое строковое представление комментария.

        Returns:
            Информация об авторе и фрагменте комментария.
        """
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return (
            f"Комментарий от {self.user.username} "
            f"к задаче '{self.task.title}': {preview}"
        )

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
