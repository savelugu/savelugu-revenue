# core/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def sum_list(value):
    try:
        return sum(value)
    except TypeError:
        return 0

@register.filter
def average(value):
    try:
        return round(sum(value) / len(value), 2) if value else 0
    except (TypeError, ZeroDivisionError):
        return 0

@register.filter
def max_value(value):
    try:
        return max(value)
    except ValueError:
        return None

@register.filter
def index(value, i):
    try:
        return value[i]
    except (IndexError, TypeError):
        return None
from django import template

register = template.Library()

@register.filter
def sum_list(value):
    try:
        return sum(value)
    except TypeError:
        return 0

@register.filter
def average(value):
    try:
        return round(sum(value) / len(value), 2) if value else 0
    except (TypeError, ZeroDivisionError):
        return 0

@register.filter
def max_value(value):
    try:
        return max(value)
    except ValueError:
        return None

@register.filter
def max_index(value):
    try:
        return value.index(max(value))
    except (ValueError, TypeError):
        return None

@register.filter
def index(value, i):
    try:
        return value[i]
    except (IndexError, TypeError):
        return None

@register.filter
def min_value(value):
    return min(value) if value else None

@register.filter
def min_index(value):
    return value.index(min(value)) if value else None

@register.filter
def forecast_accuracy(actual, predicted):
    try:
        errors = [abs(a - p) for a, p in zip(actual, predicted)]
        avg_error = sum(errors) / len(errors) if errors else 0
        return round(avg_error, 2)
    except Exception:
        return None

