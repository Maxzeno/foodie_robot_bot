"""
Admin configuration for Meal and MealEmbedding models.
"""
from django import forms
from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Count
from django.utils.html import format_html

from api.models.meal import Meal, TimeOfDayChoices
from api.models.meal_embedding import MealEmbedding


TIME_OF_DAY_STYLES = {
    'morning': ('🌅', '#ff9800', '#fff3e0'),      # Orange - sunrise
    'afternoon': ('☀️', '#2196f3', '#e3f2fd'),    # Blue - sunny
    'evening': ('🌙', '#673ab7', '#ede7f6'),      # Purple - moon
}


class MealAdminForm(forms.ModelForm):
    times_of_day_choices = forms.MultipleChoiceField(
        choices=TimeOfDayChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Times of Day"
    )

    available_from_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'vTimeField',
                'style': 'width: 150px; font-size: 14px;'
            }
        ),
        required=False,
        help_text="Time when this meal becomes available (24-hour format, e.g., 06:00 for breakfast)"
    )

    available_to_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'vTimeField',
                'style': 'width: 150px; font-size: 14px;'
            }
        ),
        required=False,
        help_text="Time when this meal stops being available (24-hour format, e.g., 11:00 for breakfast)"
    )

    class Meta:
        model = Meal
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.times_of_day:
            self.fields['times_of_day_choices'].initial = self.instance.times_of_day

    def clean_image_url(self):
        """Validate that uploaded image is JPG or PNG only (new uploads only)."""
        image = self.cleaned_data.get('image_url')

        # Only validate NEW uploads, not existing images
        if image and isinstance(image, UploadedFile):
            filename = getattr(image, 'name', '').lower()
            content_type = getattr(image, 'content_type', '').lower()

            # Allowed formats
            allowed_extensions = ('.jpg', '.jpeg', '.png')
            allowed_content_types = ('image/jpeg', 'image/png')

            # Check file extension
            has_valid_extension = any(filename.endswith(ext) for ext in allowed_extensions)
            has_valid_content_type = content_type in allowed_content_types

            if not has_valid_extension and not has_valid_content_type:
                # Provide specific error for WebP
                if filename.endswith('.webp') or content_type == 'image/webp':
                    raise forms.ValidationError(
                        "WebP format is not supported. Please upload a JPG or PNG image."
                    )
                raise forms.ValidationError(
                    "Only JPG and PNG images are supported. Please upload a valid image file."
                )

        return image

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.times_of_day = self.cleaned_data.get('times_of_day_choices', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    form = MealAdminForm
    list_display = [
        'image_preview', 'name', 'restaurant', 'city', 'price_display',
        'available_badge', 'stock_display', 'order_count', 'fitness_goals_display', 'times_of_day_display'
    ]
    list_filter = ['available', 'city', 'restaurant', 'fitness_goals', 'cuisine', 'created_at']
    search_fields = ['name', 'code', 'description', 'restaurant__name']
    readonly_fields = ['code', 'image_preview_large', 'created_at', 'updated_at']
    filter_horizontal = ['fitness_goals', 'restricted_health_conditions', 'restricted_allergies', 'cuisine']
    ordering = ['-created_at']
    list_per_page = 50

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'restaurant', 'city', 'note', 'description', 'price', 'available', 'daily_stock_limit', 'remaining_stock', 'image_url', 'image_preview_large')
        }),
        ('Availability', {
            'fields': ('times_of_day_choices', 'available_from_time', 'available_to_time'),
            'classes': ('collapse',),
        }),
        ('Nutrition', {
            'fields': ('calories', 'protein', 'carbs', 'fats', 'fiber', 'sugar', 'sodium', 'cholesterol', 'serving_amount_g'),
            'classes': ('collapse',)
        }),
        ('Diet & Restrictions', {
            'fields': ('fitness_goals', 'restricted_health_conditions', 'restricted_allergies', 'cuisine'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('restaurant', 'city').prefetch_related('fitness_goals').annotate(_order_count=Count('orders', distinct=True))

    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;"/>',
                obj.image_url.url
            )
        return '[No image]'
    image_preview.short_description = 'Image'

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: cover; border-radius: 8px;"/>',
                obj.image_url.url
            )
        return 'No image'
    image_preview_large.short_description = 'Preview'

    def price_display(self, obj):
        return f"{obj.price:,.2f}"
    price_display.short_description = 'Price'

    def available_badge(self, obj):
        if obj.available:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">YES</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">NO</span>'
        )
    available_badge.short_description = 'Available'

    def stock_display(self, obj):
        if obj.daily_stock_limit is None:
            return 'Unlimited'
        return f"{obj.remaining_stock or 0}/{obj.daily_stock_limit}"
    stock_display.short_description = 'Stock'

    def order_count(self, obj):
        return obj._order_count
    order_count.short_description = 'Orders'
    order_count.admin_order_field = '_order_count'

    def times_of_day_display(self, obj):
        if not obj.times_of_day:
            return '-'
        badges = []
        for time in obj.times_of_day:
            if time in TIME_OF_DAY_STYLES:
                emoji, border_color, bg_color = TIME_OF_DAY_STYLES[time]
                badges.append(
                    f'<span style="background: {bg_color}; border: 1px solid {border_color}; '
                    f'color: #333; padding: 2px 8px; border-radius: 12px; font-size: 11px; '
                    f'margin-right: 4px; white-space: nowrap;">{emoji} {time.title()}</span>'
                )
        return format_html(''.join(badges)) if badges else '-'
    times_of_day_display.short_description = 'Times of Day'

    def fitness_goals_display(self, obj):
        goals = obj.fitness_goals.all()
        if not goals:
            return '-'
        goal_names = [goal.name.replace('_', ' ').title() for goal in goals]
        return format_html(
            '<span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            ', '.join(goal_names)
        )
    fitness_goals_display.short_description = 'Fitness Goals'


@admin.register(MealEmbedding)
class MealEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['meal', 'content_hash', 'embedding_preview', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['meal__name', 'content_hash']
    readonly_fields = ['meal', 'embedding', 'content_hash', 'embedding_text', 'created_at', 'updated_at']
    ordering = ['-updated_at']

    def embedding_preview(self, obj):
        if obj.embedding:
            return f"[{len(obj.embedding)} dims]"
        return "-"
    embedding_preview.short_description = 'Embedding'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
