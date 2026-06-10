from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django import forms

from api.tasks.send_template_to_important_users import (
    send_template_to_important_users,
    get_important_users_preview
)


class SendTemplateForm(forms.Form):
    """Form for sending template messages to important users."""
    template_name = forms.CharField(
        max_length=200,
        initial="still_want_meal_recommendations",
        widget=forms.TextInput(attrs={
            'class': 'vTextField',
            'placeholder': 'Enter WhatsApp template name',
            'style': 'width: 300px;'
        }),
        help_text='The exact name of the WhatsApp template as configured in Meta Business Suite'
    )
    language_code = forms.CharField(
        max_length=10,
        initial='en_US',
        widget=forms.TextInput(attrs={
            'class': 'vTextField',
            'style': 'width: 100px;'
        }),
        help_text='Language code (e.g., en_US, en_GB)'
    )
    limit = forms.IntegerField(
        initial=100,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'vIntegerField',
            'style': 'width: 100px;'
        }),
        help_text='Maximum number of users to send to (1-1000)'
    )


class TemplateCampaignAdminSite:
    """Custom admin views for template campaign management."""

    @staticmethod
    @staff_member_required
    def send_template_view(request):
        """View for sending template messages to important users."""
        preview_data = None
        form = SendTemplateForm()

        if request.method == 'POST':
            action = request.POST.get('action')
            form = SendTemplateForm(request.POST)

            if form.is_valid():
                template_name = form.cleaned_data['template_name']
                language_code = form.cleaned_data['language_code']
                limit = form.cleaned_data['limit']

                if action == 'preview':
                    # Show preview of users who would receive the message
                    preview_data = get_important_users_preview(limit=limit)
                    messages.info(
                        request,
                        f'Preview: {len(preview_data)} users would receive the template "{template_name}"'
                    )

                elif action == 'send':
                    # Actually send the template messages (synchronous)
                    try:
                        result = send_template_to_important_users(
                            template_name=template_name,
                            language_code=language_code,
                            limit=limit
                        )

                        if result.get('success'):
                            messages.success(
                                request,
                                f'Successfully sent template "{template_name}" to {result["sent_count"]} users. '
                                f'Failed: {result["failed_count"]}'
                            )
                        else:
                            messages.error(
                                request,
                                f'Failed to send template: {result.get("error", "Unknown error")}'
                            )
                    except Exception as e:
                        messages.error(request, f'Error sending template: {str(e)}')

                    return redirect('admin:send_template')

        context = {
            'title': 'Send Template to Important Users',
            'form': form,
            'preview_data': preview_data,
            'opts': {'app_label': 'api'},
            'has_permission': True,
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'is_popup': False,
            'is_nav_sidebar_enabled': True,
            'available_apps': admin.site.get_app_list(request),
        }

        return render(request, 'admin/api/send_template.html', context)

    @staticmethod
    @staff_member_required
    def preview_users_api(request):
        """API endpoint for getting user preview data."""
        limit = int(request.GET.get('limit', 100))
        preview_data = get_important_users_preview(limit=limit)

        # Serialize datetime objects
        for item in preview_data:
            if item['metrics'].get('last_activity'):
                item['metrics']['last_activity'] = item['metrics']['last_activity'].isoformat()

        return JsonResponse({'users': preview_data})
