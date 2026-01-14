from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Category, Task, Comment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
        )

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id',
            'title',
            'color',
        )

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Название категории должно содержать минимум 3 символа')
        return value

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id',
            'title',
            'description',
            'status',
            'priority',
            'due_date',
            'creation_date',
            'update_date',
            'category',
            'user',
        )
        read_only_fields = (
            'id',
            'creation_date',
            'update_date',
            'user',
        )

    def create(self, validated_data):
        user = self.context['request'].user

        task = Task.objects.create(
            user=user,
            **validated_data
        )

        return task

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Название задачи должно содержать минимум 3 символа')
        return value

    def validate_priority(self, value):
        if value not in [1, 2, 3, 4]:
            raise serializers.ValidationError('Приоритет должен быть в диапазоне от 1 до 4')
        return value

    def validate_due_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError('Срок выполнения не может быть в прошлом')
        return value

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            'id',
            'task',
            'user',
            'text',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'user',
            'created_at',
            'updated_at',
        )

    def validate_text(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Комментарий должен содержать минимум 5 символов')
        return value

    def create(self, validated_data):
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Требуется аутентификация')

        validated_data['user'] = request.user

        return Comment.objects.create(**validated_data)
