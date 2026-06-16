from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Category, Comment, Task


class TaskApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="12345678"
        )

        self.token = Token.objects.create(user=self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        self.category = Category.objects.create(
            title="Работа",
            color="#FF0000"
        )

    def create_task(self, **kwargs):
        data = {
            "title": "Тестовая задача",
            "description": "Описание задачи",
            "status": "pending",
            "priority": 3,
            "due_date": timezone.now() + timedelta(days=1),
            "category": self.category,
        }

        data.update(kwargs)

        task = Task.objects.create(
            title=data["title"],
            description=data["description"],
            status=data["status"],
            priority=data["priority"],
            due_date=data["due_date"],
            category=data["category"],
        )

        task.users.add(self.user)

        return task

    # 1
    def test_create_user(self):
        user = User.objects.create_user(
            username="new_user",
            password="12345678"
        )

        self.assertEqual(user.username, "new_user")
        self.assertTrue(
            User.objects.filter(username="new_user").exists()
        )

    # 2
    def test_create_task_api(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "Курсовая работа",
                "description": "Написать курсовую",
                "status": "pending",
                "priority": 3,
                "due_date": (
                    timezone.now() + timedelta(days=5)
                ).isoformat(),
                "category": self.category.id,
                "user_ids": [self.user.id],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            Task.objects.count(),
            1
        )

    # 3
    def test_task_title_validation(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "ab",
                "description": "Описание",
                "status": "pending",
                "priority": 3,
                "due_date": (
                    timezone.now() + timedelta(days=5)
                ).isoformat(),
                "category": self.category.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # 4
    def test_due_date_validation(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "Задача",
                "description": "Описание",
                "status": "pending",
                "priority": 3,
                "due_date": (
                    timezone.now() - timedelta(days=1)
                ).isoformat(),
                "category": self.category.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # 5
    def test_priority_validation(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "Задача",
                "description": "Описание",
                "status": "pending",
                "priority": 10,
                "due_date": (
                    timezone.now() + timedelta(days=1)
                ).isoformat(),
                "category": self.category.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # 6
    def test_get_tasks_list(self):
        self.create_task()

        response = self.client.get("/api/tasks/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data["results"]),
            1
        )

    # 7
    def test_filter_tasks_by_status(self):
        self.create_task(status="pending")

        completed_task = self.create_task(
            title="Выполненная",
            status="completed"
        )

        response = self.client.get(
            "/api/tasks/?status=completed"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data["results"]),
            1
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            completed_task.id
        )

    # 8
    def test_mark_task_complete(self):
        task = self.create_task()

        response = self.client.post(
            f"/api/tasks/{task.id}/complete/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            "completed"
        )

    # 9
    def test_mark_completed_task_twice(self):
        task = self.create_task(
            status="completed"
        )

        response = self.client.post(
            f"/api/tasks/{task.id}/complete/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # 10
    def test_comment_validation(self):
        task = self.create_task()

        response = self.client.post(
            "/api/comments/",
            {
                "task": task.id,
                "text": "123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )