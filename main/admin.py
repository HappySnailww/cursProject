from django.contrib import admin
from .models import Task, Category, Comment
from django import forms

from simple_history.admin import SimpleHistoryAdmin

from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX
from import_export import resources, fields


class TaskResource(resources.ModelResource):
    status = fields.Field(
        column_name='Статус',
        attribute='status'
    )

    class Meta:
        model = Task
        fields = (
            'id',
            'title',
            'description',
            'user__username',
            'category__title',
            'status',
            'priority',
            'due_date',
            'creation_date',
            'update_date',
        )
        export_order = fields

    def get_export_queryset(self, request):
        queryset = super().get_export_queryset(request)
        return queryset.filter(priority__gte=3)

    def dehydrate_due_date(self, obj):
        if obj.due_date:
            return obj.due_date.strftime('%d-%m-%Y')
        return ''

    def dehydrate_status(self, obj):
        return {
            'pending': 'В ожидании',
            'in_progress': 'В процессе',
            'completed': 'Завершено',
        }.get(obj.status, obj.status)

    def dehydrate_creation_date(self, obj):
        return obj.creation_date.strftime('%d-%m-%Y %H:%M')

    def dehydrate_update_date(self, obj):
        return obj.update_date.strftime('%d-%m-%Y %H:%M')

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'title', 'color')
        export_order = fields

    def dehydrate_task_set(self, category):
        return ", ".join([t.title for t in category.task_set.all()])


class TaskInline(admin.TabularInline):
    model = Task
    fields = ('title', 'status', 'priority', 'due_date')
    extra = 0
    show_change_link = True


class TaskAdminForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 80}),
        }


class CommentInline(admin.TabularInline):
    model = Comment
    fields = ('user', 'text', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = CategoryResource
    list_display = (
        'title_with_color',
        'tasks_count',
    )
    list_display_links = ('title_with_color',)
    list_filter = ('color',)
    search_fields = ('title',)
    readonly_fields = ('task_list',)
    inlines = (TaskInline,)
    date_hierarchy = None
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'color')
        }),
        ('Задачи в категории', {
            'fields': ('task_list',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Категория')
    def title_with_color(self, obj):
        if not obj.title:
            return f"Без названия ({obj.color})"
        return f"{obj.title} ({obj.color})"

    @admin.display(description='Задачи')
    def tasks_count(self, obj):
        return obj.task_set.count()

    @admin.display(description='Список задач')
    def task_list(self, obj):
        tasks = obj.task_set.all()[:10]
        if tasks:
            task_items = []
            for task in tasks:
                task_items.append(
                    f"• {task.title} ({task.get_status_display()})"
                )
            return "\n".join(task_items)
        return "Задач нет"

    task_list.short_description = 'Задачи в категории'


@admin.register(Task)
class TaskAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = TaskResource
    formats = [XLSX]
    form = TaskAdminForm
    list_display = (
        'title_with_priority',
        'user',
        'category',
        'status_display',
        'due_date_short',
        'comments_count',
        'is_overdue',
    )
    list_display_links = ('title_with_priority',)
    list_filter = ('status', 'priority', 'category', 'user', 'due_date')
    inlines = (CommentInline,)
    search_fields = (
        'title',
        'description',
        'user__username',
        'category__title',
    )
    autocomplete_fields = ('user', )
    readonly_fields = (
        'creation_date',
        'update_date',
        'days_left',
        'comments_display',
    )
    date_hierarchy = 'due_date'
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'user', 'category')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority')
        }),
        ('Даты и сроки', {
            'fields': ('due_date', 'creation_date', 'update_date', 'days_left')
        }),
        ('Комментарии', {
            'fields': ('comments_display',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Приоритет')
    def title_with_priority(self, obj):
        priority_icons = {
            1: 'Низкий',
            2: 'Средний',
            3: 'Высокий',
            4: 'Критический',
        }
        icon = priority_icons.get(obj.priority, '')
        return f"{icon} {obj.title}"

    @admin.display(description='Статус')
    def status_display(self, obj):
        status_colors = {
            'pending': 'gray',
            'in_progress': 'blue',
            'completed': 'green',
        }
        color = status_colors.get(obj.status, 'black')
        return f"{obj.get_status_display()}"

    @admin.display(description='Срок')
    def due_date_short(self, obj):
        if obj.due_date:
            return obj.due_date.strftime('%d.%m.%Y')
        return '-'

    @admin.display(description='Комментарии')
    def comments_display(self, obj):
        if hasattr(obj, 'comments'):
            comments = obj.comments.all()[:10]
            if not comments:
                return "Нет комментариев"

            result = []
            for comment in comments:
                text = comment.text
                if len(text) > 50:
                    text = text[:50] + "..."

                if comment.user and comment.created_at:
                    result.append(
                        f"{comment.user.username} ({comment.created_at.strftime('%d.%m.%Y %H:%M')}): {text}"
                    )
                else:
                    result.append(f"Комментарий: {text}")

            if result:
                return "\n".join(result)
            else:
                return "Нет комментариев для отображения"
        else:
            return "Связь с комментариями не настроена"

    @admin.display(description='Количество комментариев')
    def comments_count(self, obj):
        return obj.comments.count()

    @admin.display(description='Просроченность', boolean=True)
    def is_overdue(self, obj):
        from django.utils import timezone
        if obj.due_date and obj.status != 'completed':
            return timezone.now() > obj.due_date
        return False

    @admin.display(description='Дней осталось')
    def days_left(self, obj):
        from django.utils import timezone
        if obj.due_date:
            delta = obj.due_date - timezone.now()
            days = delta.days
            if days < 0:
                return f"Просрочено на {abs(days)} дней"
            return f"{days} дней"
        return "Срок не указан"

    days_left.short_description = 'До срока выполнения'


@admin.register(Comment)
class CommentAdmin(SimpleHistoryAdmin):
    list_display = (
        'truncated_text',
        'task_title',
        'user',
        'created_at_short',
        'updated_at_short',
    )
    list_display_links = ('truncated_text',)
    list_filter = ('task', 'user', 'created_at')
    search_fields = (
        'text',
        'task__title',
        'user__username',
    )
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Основная информация', {
            'fields': ('task', 'user', 'text')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Комментарий')
    def truncated_text(self, obj):
        if len(obj.text) > 50:
            return f"{obj.text[:50]}..."
        return obj.text

    @admin.display(description='Задача')
    def task_title(self, obj):
        return obj.task.title

    @admin.display(description='Создан')
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    @admin.display(description='Обновлен')
    def updated_at_short(self, obj):
        return obj.updated_at.strftime('%d.%m.%Y %H:%M')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'user')


admin.site.site_header = "Управление задачами"
admin.site.site_title = "Админ-панель"
admin.site.index_title = "Менеджер задач"