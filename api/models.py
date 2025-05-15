# api/models.py

from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid

class Librarian(models.Model):
    name = models.CharField(max_length=200, verbose_name="Аты-жөнү")
    employee_id = models.CharField(max_length=50, unique=True, verbose_name="Кызматтык ID")
    # ImageField чыныгы сүрөт жүктөө үчүн, CharField жөн гана жолду сактоо үчүн
    photo = models.ImageField(upload_to='librarians/', blank=True, null=True, verbose_name="Сүрөтү")
    info = models.TextField(blank=True, null=True, verbose_name="Кошумча маалымат")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Китепканачы"
        verbose_name_plural = "Китепканачылар"

class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name="Аталышы")
    author = models.CharField(max_length=255, verbose_name="Автору")
    isbn = models.CharField(max_length=20, unique=True, verbose_name="ISBN")
    year_published = models.PositiveIntegerField(blank=True, null=True, verbose_name="Басылган жылы")
    quantity_total = models.PositiveIntegerField(default=1, verbose_name="Жалпы саны")
    quantity_available = models.PositiveIntegerField(default=1, verbose_name="Жеткиликтүү саны")
    genre = models.CharField(max_length=100, blank=True, null=True, verbose_name="Жанры")
    image_cover = models.ImageField(upload_to='book_covers/', blank=True, null=True, verbose_name="Китептин сүрөтү")
    loan_count = models.PositiveIntegerField(default=0, editable=False, verbose_name="Канча жолу алынган")

    def __str__(self):
        return f"{self.title} ({self.isbn})"

    def save(self, *args, **kwargs):
        # Жаңы китеп кошулганда же quantity_total өзгөргөндө quantity_available текшерүү
        if self.pk is None: # Жаңы объект
            self.quantity_available = self.quantity_total
        # Эгер quantity_available quantity_total'дан ашып кетсе же терс болсо
        if self.quantity_available > self.quantity_total:
            self.quantity_available = self.quantity_total
        if self.quantity_available < 0:
            self.quantity_available = 0
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Китеп"
        verbose_name_plural = "Китептер"
        ordering = ['title']


class Borrower(models.Model):
    USER_TYPE_CHOICES = [
        ('student', 'Окуучу'),
        ('teacher', 'Мугалим'),
    ]
    user_id = models.CharField(max_length=50, unique=True, verbose_name="Колдонуучунун ID'си")
    name = models.CharField(max_length=200, verbose_name="Аты-жөнү")
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, verbose_name="Колдонуучунун тиби")

    def __str__(self):
        return f"{self.name} ({self.get_user_type_display()})"

    class Meta:
        verbose_name = "Карыз алуучу"
        verbose_name_plural = "Карыз алуучулар"

class LoanRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='loans', verbose_name="Китеп") # Китеп өчүрүлсө, карыз кала берсин
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='loans', verbose_name="Карыз алуучу")
    loan_date = models.DateField(default=timezone.now, verbose_name="Берилген күнү")
    due_date = models.DateField(verbose_name="Кайтаруу мөөнөтү")
    return_date = models.DateField(blank=True, null=True, verbose_name="Кайтарылган күнү")

    def __str__(self):
        return f"'{self.book.title}' китеби '{self.borrower.name}'га берилген"

    @property
    def is_overdue(self):
        if self.return_date is None and timezone.now().date() > self.due_date:
            return True
        return False

    def save(self, *args, **kwargs):
        # Эгер due_date берилбесе, демейки 14 күн кошуу
        if not self.due_date and self.loan_date:
             self.due_date = self.loan_date + timedelta(days=14) # Мисалы, 14 күн
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Китеп берүү/кайтаруу жазуусу"
        verbose_name_plural = "Китеп берүү/кайтаруу жазуулары"
        ordering = ['-loan_date']