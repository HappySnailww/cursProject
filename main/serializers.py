from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import Category, Comment, Task


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "title",
            "color",
        )

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Название категории должно содержать минимум 3 символа"
            )
        return value


class TaskSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    user_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        source="users"
    )
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "creation_date",
            "update_date",
            "category",
            "users",
            "user_ids",
        )
        read_only_fields = (
            "id",
            "creation_date",
            "update_date",
            "users",
        )

    def create(self, validated_data):
        users = validated_data.pop("users", [])
        task = Task.objects.create(**validated_data)
        if not users:
            task.users.add(self.context["request"].user)
        else:
            task.users.set(users)
        return task

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Название задачи должно содержать минимум 3 символа"
            )
        return value

    def validate_priority(self, value):
        if value not in [1, 2, 3, 4]:
            raise serializers.ValidationError(
                "Приоритет должен быть в диапазоне от 1 до 4"
            )
        return value

    def validate_due_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Срок выполнения не может быть в прошлом")
        return value


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "task",
            "user",
            "text",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "created_at",
            "updated_at",
        )

    def validate_text(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Комментарий должен содержать минимум 5 символов"
            )
        return value

    def create(self, validated_data):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Требуется аутентификация")

        validated_data["user"] = request.user

        return Comment.objects.create(**validated_data)
