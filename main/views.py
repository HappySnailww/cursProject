from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Task, Comment
from .serializers import (CategorySerializer, TaskSerializer, CommentSerializer,)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        queryset = Task.objects.filter(
            Q(user=user) & (Q(status='pending') | Q(status='in_progress')) & Q(priority__gte=3) &
            ~Q(status='completed') &
            ~Q(due_date__lt=now)
        )

        extra_queryset = Task.objects.filter(
            Q(user=user) &
            Q(status='pending') &
            Q(priority__lte=2) &
            ~Q(category__title='Работа')
        )

        queryset = queryset | extra_queryset

        return queryset.distinct()

    @action(methods=['GET'], detail=False, url_path='overdue')
    def overdue_tasks(self, request):
        user = request.user
        now = timezone.now()
        tasks = Task.objects.filter(
            user=user,
            due_date__lt=now,
            status__in=['pending', 'in_progress']
        )
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(methods=['POST'], detail=True, url_path='complete')
    def mark_complete(self, request, pk=None):
        try:
            task = Task.objects.get(pk=pk, user=request.user)
        except Task.DoesNotExist:
            return Response({'detail': 'Задача не найдена или не принадлежит пользователю'}, status=404)

        if task.status == 'completed':
            return Response({'detail': 'Задача уже выполнена'}, status=status.HTTP_400_BAD_REQUEST)

        task.status = 'completed'
        task.update_date = timezone.now()
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return Comment.objects.filter(task__user=user)
