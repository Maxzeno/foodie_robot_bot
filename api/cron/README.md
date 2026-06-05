# Cron Jobs Documentation

This directory contains cron job functions for automated tasks in the Foodie Robot backend.

## Available Cron Jobs

### 1. Remind Users to Reply (`remind_user_to_reply.py`)

**Purpose:** Keep users within WhatsApp's 24-hour free messaging window by reminding them to reply.

**When it runs:** Every hour (recommended)

**What it does:**
- Finds users whose last message was 23-24 hours ago
- Sends them a reminder to reply to keep receiving meal recommendations
- Prevents duplicate reminders within the same 24-hour period
- Uses `NEEDS_REPLY` intent to track reminder messages

**Why it's important:**
WhatsApp only allows free messaging within 24 hours of the user's last reply. After that, you need to pay for template messages. By prompting users to reply before the 24-hour window closes, we can:
- Keep the conversation within the free messaging window
- Maintain user engagement
- Reduce messaging costs

---

## Testing Cron Jobs

### Using the Management Command

We provide a Django management command for easy testing and manual execution.

#### 1. Dry Run (Preview Mode)
See which users would be reminded without actually sending messages:

```bash
python manage.py remind_users --dry-run
```

Output example:
```
DRY RUN MODE - No messages will be sent

Found 3 user(s) who need reminders:

  • +2348012345678 - Last reply: 2025-12-01 14:30:00 (23.5 hours ago)
  • +2348087654321 - Last reply: 2025-12-01 14:15:00 (23.7 hours ago)
  • +2348098765432 - Last reply: 2025-12-01 14:00:00 (23.9 hours ago)

Would send 3 reminder(s)
```

#### 2. Normal Execution
Actually send the reminders:

```bash
python manage.py remind_users
```

#### 3. Test with Specific User
Test the reminder with a specific phone number:

```bash
python manage.py remind_users --test-user +2348012345678
```

#### 4. Force Send (for testing)
Force send a reminder even if one was recently sent:

```bash
python manage.py remind_users --test-user +2348012345678 --force
```

---

## Setting Up Automated Cron Jobs

There are several ways to schedule these jobs to run automatically:

### Option 1: System Crontab (Linux/Mac)

1. Open your crontab:
```bash
crontab -e
```

2. Add this line to run every hour:
```cron
0 * * * * cd /path/to/foodie_robot_backend && /path/to/python manage.py remind_users >> /var/log/remind_users.log 2>&1
```

Example with actual paths:
```cron
0 * * * * cd /home/ubuntu/foodie_robot_backend && /home/ubuntu/foodie_robot_backend/env/bin/python manage.py remind_users >> /var/log/remind_users.log 2>&1
```

**Explanation:**
- `0 * * * *` - Run at minute 0 of every hour
- `cd /path/to/foodie_robot_backend` - Navigate to project directory
- `/path/to/python manage.py remind_users` - Run the management command
- `>> /var/log/remind_users.log 2>&1` - Log output to file

### Option 2: Django Crontab Package

1. Install django-crontab:
```bash
pip install django-crontab
```

2. Add to `INSTALLED_APPS` in settings.py:
```python
INSTALLED_APPS = [
    # ... other apps
    'django_crontab',
]
```

3. Add to settings.py:
```python
CRONJOBS = [
    # Run every hour
    ('0 * * * *', 'api.cron.remind_user_to_reply.remind_users_to_reply'),
]
```

4. Install the cron jobs:
```bash
python manage.py crontab add
```

5. View active cron jobs:
```bash
python manage.py crontab show
```

6. Remove cron jobs (if needed):
```bash
python manage.py crontab remove
```

### Option 3: Celery Beat (Recommended for Production)

If you're already using Celery:

1. Create a Celery task in `api/tasks.py`:
```python
from celery import shared_task
from api.cron.remind_user_to_reply import remind_users_to_reply

@shared_task
def remind_users_task():
    return remind_users_to_reply()
```

2. Configure in `celery.py`:
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'remind-users-every-hour': {
        'task': 'api.tasks.remind_users_task',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

3. Start Celery Beat:
```bash
celery -A foodie_robot beat --loglevel=info
```

### Option 4: Heroku Scheduler (For Heroku Deployments)

1. Add Heroku Scheduler add-on:
```bash
heroku addons:create scheduler:standard
```

2. Open scheduler dashboard:
```bash
heroku addons:open scheduler
```

3. Add job:
   - Command: `python manage.py remind_users`
   - Frequency: Every hour
   - Dyno size: Standard-1X

### Option 5: AWS CloudWatch Events (For AWS Deployments)

1. Create a Lambda function that triggers your Django management command
2. Set up CloudWatch Event Rule with cron expression: `cron(0 * * * ? *)`
3. Configure Lambda to run hourly

---

## Monitoring and Logs

### Check Logs

The cron job logs important information:
- Number of users reminded
- Users already reminded (skipped)
- Errors encountered

Enable logging in your Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/cron.log',
        },
    },
    'loggers': {
        'api.cron': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Monitor Performance

Track these metrics:
- Reminder success rate
- User response rate after reminders
- Time to send all reminders
- Error rate

You can query the database to check:

```python
from api.models.message import Message, CurrentIntentChoices
from django.utils import timezone
from datetime import timedelta

# Reminders sent in last 24 hours
twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
reminders_sent = Message.objects.filter(
    role='bot',
    current_intent=CurrentIntentChoices.NEEDS_REPLY,
    created_at__gte=twenty_four_hours_ago
).count()

print(f"Reminders sent in last 24h: {reminders_sent}")
```

---

## Troubleshooting

### Users not receiving reminders

**Check:**
1. Is the cron job actually running?
   ```bash
   python manage.py remind_users --dry-run
   ```

2. Are there users in the 23-24 hour window?
   ```python
   from api.cron.remind_user_to_reply import get_users_needing_reminder
   users = get_users_needing_reminder()
   print(f"Users needing reminder: {len(users)}")
   ```

3. Check WhatsApp API credentials in settings
4. Check logs for errors

### Duplicate reminders being sent

**Check:**
- The code checks for existing `NEEDS_REPLY` messages
- Ensure the cron job isn't running too frequently (should be hourly)
- Check if multiple cron jobs are set up accidentally

### Cron job not running on schedule

**Check:**
1. Crontab syntax: `crontab -l` to list jobs
2. Cron service status: `sudo service cron status`
3. File permissions: Ensure Python script is executable
4. Environment variables: Cron may not have same env as your shell

---

## Testing Checklist

Before deploying to production:

- [ ] Test dry-run mode
- [ ] Test with a real user account
- [ ] Verify reminder message format
- [ ] Check that duplicate reminders are prevented
- [ ] Verify logging works
- [ ] Test timezone handling
- [ ] Ensure WhatsApp API is working
- [ ] Monitor for a few days in production

---

## Time Window Logic

```
User's last message
        |
        v
    [0 hours]------------------------[23 hours]----------[24 hours]
                                          ^                   ^
                                          |                   |
                                    Reminder sent      Free window closes
                                    (23-24h window)    (Need paid templates)
```

**Key Points:**
- WhatsApp free messaging window: 24 hours after user's last message
- Reminder window: 23-24 hours after user's last message
- This gives users 1 hour to reply and stay in the free window
- If they reply, the 24-hour clock resets

---

## Future Enhancements

Consider adding:
1. **Customizable reminder message** - Different messages for different user segments
2. **Smart timing** - Send reminders at optimal times based on user's timezone/activity
3. **Reminder preferences** - Let users opt out of reminders
4. **Multiple reminder levels** - Escalating reminders at 22h, 23h, 23.5h
5. **Analytics dashboard** - Track reminder effectiveness
6. **A/B testing** - Test different reminder messages to improve response rates

---

## Related Files

- Cron function: `/api/cron/remind_user_to_reply.py`
- Management command: `/api/management/commands/remind_users.py`
- Message model: `/api/models/message.py`
- User model: `/api/models/user.py`

---

## Support

For questions or issues:
1. Check logs first
2. Run dry-run mode to debug
3. Test with specific user
4. Review this documentation
