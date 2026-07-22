from .models import Notification


def notify(recipient, *, title, message, category=Notification.Category.ACCOUNT, destination=""):
    """Create durable participant feedback from account and workflow events."""
    return Notification.objects.create(
        recipient=recipient,
        category=category,
        title=title,
        message=message,
        destination=destination,
    )
