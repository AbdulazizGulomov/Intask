# apps/accounts/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

from apps import jobs
from apps.accounts import auth


class UserManager(BaseUserManager):
    def create_user(self, phone=None, username=None, password=None, **extra_fields):
        """
        - Workers/Employers: phone required (OTP), password unused
        - Admins: username + password
        """
        if not phone and not username:
            raise ValueError("Either phone or username is required")

        if phone:
            phone = str(phone).strip()
        if username:
            username = str(username).strip()

        user = self.model(phone=phone, username=username, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # OTP users

        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Username is required for superuser")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        return self.create_user(username=username, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        WORKER = "worker", "Worker"
        EMPLOYER = "employer", "Employer"
        OPERATOR = "operator", "Operator"
        ADMIN = "admin", "Admin"

    # Admin login (optional)
    username = models.CharField(max_length=60, unique=True, null=True, blank=True)

    # OTP login (main)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WORKER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    # OTP login identifier
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["username"]

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_("The groups this user belongs to."),
        related_name="accounts_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="accounts_user_permissions",
        related_query_name="user",
    )

    def __str__(self):
        return self.phone or self.username or f"User({self.pk})"


class WorkerProfile(models.Model):
    """
    Worker registration info:
    - first_name
    - last_name
    - age
    - gender
    - photo
    - profession
    - certificate
    """

    class Gender(models.TextChoices):
        MALE = "male", _("Erkak")
        FEMALE = "female", _("Ayol")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="worker_profile",
    )

    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    photo = models.ImageField(
        upload_to="worker_photos/",
        blank=True,
        null=True,
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        null=True,
        blank=True,

    )

    full_name = models.CharField(max_length=120, blank=True)

    profession = models.ForeignKey(
        "jobs.Profession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worker_profiles",
    )

    certificate = models.FileField(
        upload_to="worker_certificates/",
        null=True,
        blank=True,
    )

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.full_name or f"{self.first_name} {self.last_name}".strip()
        return f"WorkerProfile({name or self.user_id})"