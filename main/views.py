from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter, SearchFilter

from .forms import TaskForm
from .models import Category, Comment, Task
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    RegisterSerializer,
    TaskSerializer,
)


def register(request):
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


def login_view(request):
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


def logout_view(request):
    logout(request)
    return redirect("home")


def home(request):
    return render(request, "main/home.html")


@login_required
def task_list(request):
    tasks = Task.objects.filter(users=request.user).order_by("-due_date")
    return render(request, "main/task_list.html", {"tasks": tasks})


@login_required
def task_add(request):
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
def task_edit(request, pk):
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
def task_delete(request, pk):
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
def comment_add(request, task_id):
    task = get_object_or_404(Task, pk=task_id, users=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            Comment.objects.create(task=task, user=request.user, text=text)
    return redirect("task_list")


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {"username": user.username, "token": token.key},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Token.DoesNotExist:
            pass

        return Response(
            {"detail": "Вы успешно вышли из системы"}, status=status.HTTP_200_OK
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class TaskViewSet(viewsets.ModelViewSet):
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
    filterset_fields = {
        "status": ["exact"],
        "priority": ["exact", "gte", "lte"],
        "due_date": ["gte", "lte"],
    }
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Task.objects.filter(users=self.request.user)

        due_date = self.request.GET.get("due_date")
        if due_date:
            queryset = queryset.filter(due_date__date=due_date)

        return queryset

    @action(methods=["GET"], detail=False, url_path="filtered-tasks")
    def filtered_tasks(self, request):
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
    def overdue_tasks(self, request):
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

    @action(methods=["POST"], detail=True, url_path="complete")
    def mark_complete(self, request, pk=None):
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
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Comment.objects.filter(task__users=user)
