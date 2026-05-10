# apps/accounts/dashboard/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User


class OperatorLoginSerializer(serializers.Serializer):
    """
    Validates phone + password and returns the authenticated user.
    Only operators and admins are allowed in via this endpoint.
    """

    phone = serializers.CharField(max_length=20, required=True)
    password = serializers.CharField(
        max_length=128,
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_phone(self, value: str) -> str:
        phone = (value or "").strip()
        if not phone:
            raise serializers.ValidationError(_("Phone is required."))
        # Normalize: ensure leading + for international format
        if not phone.startswith("+"):
            phone = "+" + phone
        return phone

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        # Try authenticating against the User model
        user = authenticate(
            request=self.context.get("request"),
            phone=phone,
            password=password,
        )

        # Fallback: if the custom backend doesn't support phone kwarg,
        # try matching the user manually then check_password.
        if user is None:
            try:
                candidate = User.objects.get(phone=phone)
                if candidate.check_password(password):
                    user = candidate
            except User.DoesNotExist:
                user = None

        if user is None:
            raise serializers.ValidationError(
                {"detail": _("Invalid phone or password.")}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": _("This account is deactivated.")}
            )

        # Restrict to operators and admins only
        role = getattr(user, "role", None)
        if role not in (User.Role.OPERATOR, User.Role.ADMIN) and not user.is_superuser:
            raise serializers.ValidationError(
                {"detail": _("This account is not authorized to access the dashboard.")}
            )

        attrs["user"] = user
        return attrs


class OperatorMeSerializer(serializers.ModelSerializer):
    """Returned by /api/dashboard/auth/me/ — what the React app needs about the logged-in user."""

    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "username",
            "role",
            "is_staff",
            "is_superuser",
            "is_active",
        )
        read_only_fields = fields
# =====================================================
# Order serializers (for /api/dashboard/orders/)
# =====================================================
from apps.orders.models import Order, OrderStatusHistory
from apps.jobs.models import Profession


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_phone = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_phone",
            "note",
            "created_at",
        )
        read_only_fields = fields

    def get_changed_by_phone(self, obj):
        if obj.changed_by:
            return obj.changed_by.phone or obj.changed_by.username
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Slim version for the orders table."""
    employer_phone = serializers.SerializerMethodField()
    worker_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "title",
            "employer_phone",
            "worker_phone",
            "status",
            "status_display",
            "agreed_price",
            "currency",
            "address",
            "scheduled_at",
            "created_at",
        )
        read_only_fields = fields

    def get_employer_phone(self, obj):
        return obj.employer.phone if obj.employer else None

    def get_worker_phone(self, obj):
        return obj.worker.phone if obj.worker else None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full version for the order detail page."""
    employer_phone = serializers.SerializerMethodField()
    worker_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "title",
            "description",
            "employer",
            "employer_phone",
            "worker",
            "worker_phone",
            "status",
            "status_display",
            "agreed_price",
            "currency",
            "scheduled_at",
            "started_at",
            "completed_at",
            "address",
            "lat",
            "lng",
            "employer_rating",
            "worker_rating",
            "employer_review",
            "worker_review",
            "cancellation_reason",
            "status_history",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "employer",
            "worker",
            "status_display",
            "status_history",
            "created_at",
            "updated_at",
        )

    def get_employer_phone(self, obj):
        return obj.employer.phone if obj.employer else None

    def get_worker_phone(self, obj):
        return obj.worker.phone if obj.worker else None


class OrderUpdateSerializer(serializers.ModelSerializer):
    """What operators are allowed to change."""

    class Meta:
        model = Order
        fields = (
            "status",
            "scheduled_at",
            "address",
            "lat",
            "lng",
            "agreed_price",
            "cancellation_reason",
        )

    def update(self, instance, validated_data):
        # Track status changes in history
        old_status = instance.status
        new_status = validated_data.get("status", old_status)

        instance = super().update(instance, validated_data)

        if old_status != new_status:
            request = self.context.get("request")
            OrderStatusHistory.objects.create(
                order=instance,
                from_status=old_status,
                to_status=new_status,
                changed_by=request.user if request else None,
                note=f"Changed via dashboard by {request.user.phone if request else 'system'}",
            )

            # Auto-update timestamps
            if new_status == Order.Status.IN_PROGRESS and not instance.started_at:
                from django.utils import timezone
                instance.started_at = timezone.now()
                instance.save(update_fields=["started_at"])
            elif new_status == Order.Status.COMPLETED and not instance.completed_at:
                from django.utils import timezone
                instance.completed_at = timezone.now()
                instance.save(update_fields=["completed_at"])

        return instance


# =====================================================
# Master serializers (for /api/dashboard/masters/)
# =====================================================
from apps.accounts.models import WorkerProfile


class MasterListSerializer(serializers.ModelSerializer):
    """Worker info for the masters page."""
    phone = serializers.CharField(source="user.phone", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    profession_name = serializers.CharField(source="profession.name", read_only=True, default=None)
    completed_orders = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = WorkerProfile
        fields = (
            "id",
            "user_id",
            "phone",
            "is_active",
            "first_name",
            "last_name",
            "full_name",
            "age",
            "gender",
            "profession",
            "profession_name",
            "is_completed",
            "completed_orders",
            "avg_rating",
            "created_at",
        )
        read_only_fields = fields

    def get_completed_orders(self, obj):
        return Order.objects.filter(
            worker=obj.user,
            status=Order.Status.COMPLETED,
        ).count()

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = Order.objects.filter(
            worker=obj.user,
            status=Order.Status.COMPLETED,
            employer_rating__isnull=False,
        ).aggregate(avg=Avg("employer_rating"))
        avg = result["avg"]
        return round(avg, 2) if avg is not None else None
