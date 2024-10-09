from otree.models import ParticipantRoomVisit
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ParticipantRoomVisit)
def log_participant_room_visit(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Participant {instance.participant.code} connected at {instance.last_updated}")
    else:
        time_difference = timezone.now() - instance.last_updated
        if time_difference.total_seconds() > 5:  # Adjust this threshold as needed
            logger.warning(f"Participant {instance.participant.code} disconnected for {time_difference.total_seconds()} seconds")

class DisconnectionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response