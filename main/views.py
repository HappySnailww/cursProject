from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import sentry_sdk

from .filters import TaskFilter
from .forms import TaskForm
from .models import Category, Comment, Task
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    RegisterSerializer,
    TaskSerializer,
)


def register(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """
    Регистрирует нового пользователя.

    Проверяет корректность введенных данных, создает пользователя
    и выполняет автоматический вход в систему.

    Args:
        request: HTTP-запрос.

    Returns:
        Страница регистрации или перенаправление на список задач.
    """
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()
        password2 = request.POST.get("password2").strip()

        if not username or not password or not password2:
            messages.error(request, "Заполните все поля")
        elif password != password2:
            messages.error(request, "Пароли не совпадают")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Пользователь с таким именем уже существует")
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect("task_list")

    return render(request, "main/register.html")


def login_view(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """
    Выполняет аутентификацию пользователя.

    Args:
        request: HTTP-запрос.

    Returns:
        Страница входа или перенаправление на список задач.
    """
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("task_list")
        else:
            messages.error(request, "Неверный логин или пароль")
    return render(request, "main/login.html")


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Завершает текущую пользовательскую сессию.

    Args:
        request: HTTP-запрос.

    Returns:
        Перенаправление на главную страницу.
    """
    logout(request)
    return redirect("home")


def home(request: HttpRequest) -> HttpResponse:
    """
    Отображает главную страницу приложения.

    Args:
        request: HTTP-запрос.

    Returns:
        HTML-страница.
    """
    return render(request, "main/home.html")


@login_required
def task_list(request: HttpRequest) -> HttpResponse:
    """
    Отображает список задач текущего пользователя.

    Args:
        request: HTTP-запрос.

    Returns:
        HTML-страница со списком задач.
    """
    tasks = Task.objects.filter(users=request.user).order_by("-due_date")
    return render(request, "main/task_list.html", {"tasks": tasks})


@login_required
def task_add(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """
    Создает новую задачу и привязывает ее к пользователю.

    Args:
        request: HTTP-запрос.

    Returns:
        Форма создания задачи или перенаправление после сохранения.
    """
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            task.users.add(request.user)
            return redirect("task_list")
    else:
        form = TaskForm()
    return render(request, "main/task_add.html", {"form": form})


@login_required
def task_edit(request: HttpRequest, pk: int,) -> HttpResponse | HttpResponseRedirect:
    """
    Редактирует существующую задачу пользователя.

    Args:
        request: HTTP-запрос.
        pk: Идентификатор задачи.

    Returns:
        Страница редактирования или перенаправление.
    """
    try:
        task = Task.objects.get(pk=pk, users=request.user)
    except Task.DoesNotExist:
        messages.error(request, "Задача не найдена или не принадлежит вам")
        return redirect("task_list")

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Задача успешно обновлена")
            return redirect("task_list")
    else:
        form = TaskForm(instance=task)

    return render(request, "main/task_add.html", {"form": form, "edit": True})


@login_required
def task_delete(request: HttpRequest, pk: int,) -> HttpResponse | HttpResponseRedirect:
    """
    Удаляет задачу пользователя.

    Args:
        request: HTTP-запрос.
        pk: Идентификатор задачи.

    Returns:
        Страница подтверждения удаления или перенаправление.
    """
    try:
        task = Task.objects.get(pk=pk, users=request.user)
    except Task.DoesNotExist:
        messages.error(request, "Задача не найдена или не принадлежит вам")
        return redirect("task_list")

    if request.method == "POST":
        task.delete()
        messages.success(request, "Задача удалена")
        return redirect("task_list")

    return render(request, "main/task_delete.html", {"task": task})


@login_required
def comment_add(request: HttpRequest, task_id: int,) -> HttpResponseRedirect:
    """
    Добавляет комментарий к задаче.

    Args:
        request: HTTP-запрос.
        task_id: Идентификатор задачи.

    Returns:
        Перенаправление на список задач.
    """
    task = get_object_or_404(Task, pk=task_id, users=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            Comment.objects.create(task=task, user=request.user, text=text)
    return redirect("task_list")

def sentry_test(request: HttpRequest) -> HttpResponse:
    """
    Отправляет тестовую ошибку в Sentry.

    Args:
        request: HTTP-запрос.

    Returns:
        Информация об отправке события в Sentry.
    """
    try:
        division_by_zero = 1 / 0
    except ZeroDivisionError:
        sentry_sdk.capture_exception()
        
        last_event_id = sentry_sdk.last_event_id()
        if last_event_id:
            return HttpResponse(f"Ошибка отправлена. Event ID: {last_event_id}")
        else:
            return HttpResponse("Ошибка НЕ отправлена")

class RegisterView(APIView):
    """
    API для регистрации пользователя и выдачи токена авторизации.
    """
    permission_classes = [AllowAny]

    def post(self, request) -> Response:
        """
        Создает пользователя и возвращает токен.

        Args:
            request: HTTP-запрос с регистрационными данными.

        Returns:
            Response с именем пользователя и токеном.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {"username": user.username, "token": token.key},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """
    API для выхода пользователя из системы.
    """
    def post(self, request) -> Response:
        """
        Удаляет токен текущего пользователя.

        Args:
            request: HTTP-запрос.

        Returns:
            Сообщение об успешном выходе.
        """
        try:
            request.user.auth_token.delete()
        except Token.DoesNotExist:
            pass

        return Response(
            {"detail": "Вы успешно вышли из системы"}, status=status.HTTP_200_OK
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра категорий задач.

    Дополнительно содержит количество выполненных задач
    в каждой категории.
    """
    queryset = Category.objects.annotate(completed_tasks_count=Count("task", filter=Q(task__status="completed")))
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD API для работы с задачами пользователя.

    Поддерживает фильтрацию, поиск, сортировку
    и дополнительные пользовательские действия.
    """
    serializer_class = TaskSerializer

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
        SearchFilter,
    ]
    search_fields = [
        "title",
        "description",
        "category__title",
    ]
    filterset_class = TaskFilter
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Task]:
        """
        Возвращает задачи текущего пользователя.

        Returns:
            QuerySet задач.
        """
        queryset = (
            Task.objects.filter(
                users=self.request.user
            )
            .select_related("category")
            .prefetch_related("users")
            .annotate(comments_count=Count("comments",distinct=True),users_count=Count("users",distinct=True),)
        )

        due_date = self.request.GET.get("due_date")

        if due_date:
            queryset = queryset.filter(
                due_date__date=due_date
            )

        return queryset
    
    def get_serializer_context(self) -> dict:
        """
        Передает текущего пользователя в контекст сериализатора.

        Returns:
            Словарь контекста сериализатора.
        """
        context = super().get_serializer_context()
        context["current_user"] = self.request.user

        return context

    @action(methods=["GET"], detail=False, url_path="filtered-tasks")
    def filtered_tasks(self, request) -> Response:
        """
        Возвращает задачи по сложному набору условий.

        Args:
            request: HTTP-запрос.

        Returns:
            Список отфильтрованных задач.
        """
        user = request.user
        now = timezone.now()

        main_queryset = Task.objects.filter(
            Q(users=user)
            & (Q(status="pending") | Q(status="in_progress"))
            & Q(priority__gte=3)
            & ~Q(status="completed")
            & ~Q(due_date__lt=now)
        )

        extra_queryset = Task.objects.filter(
            Q(users=user)
            & Q(status="pending")
            & Q(priority__lte=2)
            & ~Q(category__title="Работа")
        )

        queryset = (main_queryset | extra_queryset).distinct()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["GET"], detail=False, url_path="overdue")
    def overdue_tasks(self, request) -> Response:
        """
        Возвращает просроченные задачи пользователя.

        Args:
            request: HTTP-запрос.

        Returns:
            Список просроченных задач.
        """
        user = request.user
        now = timezone.now()
        tasks = Task.objects.filter(
            users=user, due_date__lt=now, status__in=["pending", "in_progress"]
        )
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(methods=["GET"], detail=False, url_path="statistics")
    def statistics(self, request) -> Response:
        """
        Возвращает статистику по задачам пользователя.

        Args:
            request: HTTP-запрос.

        Returns:
            Количество просроченных задач.
        """
        overdue_count = Task.objects.filter(
            users=request.user,
            due_date__lt=timezone.now()
        ).exclude(
            status="completed"
        ).count()

        return Response(
            {
                "overdue_tasks_count":
                    overdue_count
            }
        )

    @action(methods=["POST"], detail=True, url_path="complete")
    def mark_complete(self, request, pk: int | None = None,) -> Response:
        """
        Помечает задачу как выполненную.

        Args:
            request: HTTP-запрос.
            pk: Идентификатор задачи.

        Returns:
            Обновленная задача или сообщение об ошибке.
        """
        try:
            task = Task.objects.get(pk=pk, users=request.user)
        except Task.DoesNotExist:
            return Response(
                {"detail": "Задача не найдена или не принадлежит пользователю"},
                status=404,
            )

        if task.status == "completed":
            return Response(
                {"detail": "Задача уже выполнена"}, status=status.HTTP_400_BAD_REQUEST
            )

        task.status = "completed"
        task.update_date = timezone.now()
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    """
    CRUD API для комментариев к задачам.
    """
    serializer_class = CommentSerializer
    def get_queryset(self) -> QuerySet[Comment]:
        """
        Возвращает комментарии к задачам текущего пользователя.

        Returns:
            QuerySet комментариев.
        """
        queryset = Comment.objects.filter(
            task__users=self.request.user
        ).select_related(
            "task",
            "user"
        )
        
        task_id = self.request.GET.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        return queryset
