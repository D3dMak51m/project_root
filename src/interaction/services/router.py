from src.interaction.interfaces.router import InteractionRouter
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility


class StandardInteractionRouter(InteractionRouter):
    """
    Deterministic router based on intent type and metadata.
    """

    def route(self, intent: InteractionIntent) -> InteractionEnvelope:

        target_hint = TargetHint.UNKNOWN
        priority_hint = PriorityHint.NORMAL
        visibility = Visibility.INTERNAL
        routing_key = None

        # 1. Route by Type
        if intent.type == InteractionType.REPORT:
            target_hint = TargetHint.ADMIN
            visibility = Visibility.INTERNAL
            priority_hint = PriorityHint.LOW

        elif intent.type == InteractionType.QUESTION:
            target_hint = TargetHint.ADMIN  # Questions usually go to admin/supervisor
            visibility = Visibility.INTERNAL
            priority_hint = PriorityHint.NORMAL

        elif intent.type == InteractionType.NOTIFICATION:
            target_hint = TargetHint.CHANNEL  # Notifications might be broadcast
            visibility = Visibility.INTERNAL  # Default to internal logs unless specified
            priority_hint = PriorityHint.NORMAL

        elif intent.type == InteractionType.MESSAGE:
            target_hint = TargetHint.USER
            visibility = Visibility.EXTERNAL
            priority_hint = PriorityHint.NORMAL

        elif intent.type == InteractionType.CONFIRMATION_REQUEST:
            target_hint = TargetHint.ADMIN
            visibility = Visibility.INTERNAL
            priority_hint = PriorityHint.HIGH

        # 2. Metadata Overrides (if present and valid)
        if intent.target_id:
            routing_key = intent.target_id

        # 3. Construct Envelope
        return InteractionEnvelope(
            intent=intent,
            target_hint=target_hint,
            priority_hint=priority_hint,
            visibility=visibility,
            routing_key=routing_key
        )