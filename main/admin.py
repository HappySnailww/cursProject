from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX
from simple_history.admin import SimpleHistoryAdmin

from .models import Category, Comment, Task


class TaskResource(resources.ModelResource):
    status = fields.Field(column_name="Статус", attribute="status")

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "user__username",
            "category__title",
            "status",
            "priority",
            "due_date",
            "creation_date",
            "update_date",
        )
        export_order = fields

    def get_export_queryset(self, request):
        queryset = super().get_export_queryset(request)
        return queryset.filter(priority__gte=3)

    def dehydrate_due_date(self, obj):
        return obj.due_date.strftime("%d-%m-%Y") if obj.due_date else ""

    def dehydrate_status(self, obj):
        return {
            "pending": "В ожидании",
            "in_progress": "В процессе",
            "completed": "Завершено",
        }.get(obj.status, obj.status)

    def dehydrate_creation_date(self, obj):
        return obj.creation_date.strftime("%d-%m-%Y %H:%M")

    def dehydrate_update_date(self, obj):
        return obj.update_date.strftime("%d-%m-%Y %H:%M")


class TaskInline(admin.TabularInline):
    model = Task
    fields = ("title", "status", "priority")
    extra = 0
    show_change_link = True


class CommentInline(admin.TabularInline):
    model = Comment
    fields = ("user", "text", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin):
    list_display = ("title_with_color", "tasks_count")
    list_display_links = ("title_with_color",)
    list_filter = ("color",)
    search_fields = ("title",)
    inlines = (TaskInline,)

    fieldsets = (("Основная информация", {"fields": ("title", "color")}),)

    @admin.display(description="Категория")
    def title_with_color(self, obj):
        return f"{obj.title} ({obj.color})"

    @admin.display(description="Количество задач")
    def tasks_count(self, obj):
        return obj.task_set.count()


@admin.register(Task)
class TaskAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = TaskResource
    formats = [XLSX]

    list_display = (
        "title",
        "user",
        "category",
        "status",
        "priority",
        "due_date",
    )
    list_display_links = ("title",)
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description")
    raw_id_fields = ("user",)
    readonly_fields = ("creation_date", "update_date")
    date_hierarchy = "due_date"
    inlines = (CommentInline,)

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("title", "description", "user", "category")},
        ),
        ("Статус и приоритет", {"fields": ("status", "priority")}),
        ("Даты", {"fields": ("due_date", "creation_date", "update_date")}),
    )


@admin.register(Comment)
class CommentAdmin(SimpleHistoryAdmin):
    list_display = ("short_text", "task", "user", "created_at")
    list_display_links = ("short_text",)
    list_filter = ("task", "user", "created_at")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("task", "user")

    fieldsets = (
        ("Комментарий", {"fields": ("task", "user", "text")}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Комментарий")
    def short_text(self, obj):
        return obj.text[:50] + ("..." if len(obj.text) > 50 else "")
