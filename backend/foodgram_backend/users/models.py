from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    """Модель пользователя."""
    REQUIRED_FIELDS = [
        'username',
        'first_name',
        'last_name',
    ]
    USERNAME_FIELD = 'email'

    username = models.CharField(
        unique=True,
        max_length=150,
        validators=[UnicodeUsernameValidator(), ],
        verbose_name='Никнейм пользователя',
        help_text='Укажите никнейм пользователя'
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
        help_text='Укажите имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
        help_text='Укажите фамилию'
    )
    email = models.EmailField(
        unique=True,
        max_length=254,
        verbose_name='Email',
        help_text='Укажите email',
    )
    avatar = models.ImageField(
        upload_to='users/',
        null=True,
        blank=True,
        verbose_name='Аватар',
        help_text='Прикрепите аватар')

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Subscribers(models.Model):
    """Модель подписок."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name='Автор рецептов',
        help_text='Укажите автора рецепта'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Подписчик',
        help_text='Укажите подписчика'
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'user'],
                name='unique_author_user'
            ),
            models.CheckConstraint(
                check=~models.Q(author=models.F('user')),
                name='author_and_user_different',
            )
        ]

    def __str__(self):
        return f"{self.author} - {self.user}"
