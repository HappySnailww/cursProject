import django_filters
from django.utils import timezone

from .models import Task


class TaskFilter(django_filters.FilterSet):
    due_date_after = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="gte",
    )

    due_date_before = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="lte",
    )

    overdue = django_filters.BooleanFilter(
        method="filter_overdue"
    )

    completed = django_filters.BooleanFilter(
        method="filter_completed"
    )

    class Meta:
        model = Task

        fields = {
            "status": ["exact"],
            "priority": ["exact"],
            "category": ["exact"],
        }

    def filter_overdue(self, queryset, name, value):
        if value:
            return queryset.filter(
                due_date__lt=timezone.now()
            ).exclude(
                status="completed"
            )

        return queryset

    def filter_completed(self, queryset, name, value):
        if value:
            return queryset.filter(
                status="completed"
            )

        return queryset