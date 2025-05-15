# api/admin.py

from django.contrib import admin
from .models import Librarian, Book, Borrower, LoanRecord
from django.db.models import F # F() expressions үчүн

@admin.register(Librarian)
class LibrarianAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id')
    search_fields = ('name', 'employee_id')
    # readonly_fields = ('photo_preview',) # Эгер сүрөттү админкада көрсөткүңүз келсе

    # def photo_preview(self, obj):
    #     from django.utils.html import mark_safe
    #     if obj.photo:
    #         return mark_safe(f'<img src="{obj.photo.url}" width="150" />')
    #     return "(No photo)"
    # photo_preview.short_description = 'Photo Preview'

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'quantity_total', 'quantity_available', 'loan_count', 'genre')
    search_fields = ('title', 'author', 'isbn', 'genre')
    list_filter = ('genre', 'author')
    readonly_fields = ('loan_count',) # 'quantity_available' дагы этияттык менен башкарылышы керек

    def save_model(self, request, obj, form, change):
        # Админкадан quantity_total өзгөртүлсө, quantity_available'ды тууралоо
        if change and 'quantity_total' in form.changed_data:
            # Эски маанилерди алуу үчүн, бирок бул жерде татаалдашат,
            # анткени form.initial иштебеши мүмкүн же толук болбошу мүмкүн.
            # Жөнөкөй ыкма:
            books_on_loan = 0
            if obj.pk: # Эгер объект мурунтан эле бар болсо
                try:
                    # Маалымат базасынан эски жалпы санын жана жеткиликтүү санын алуу
                    old_book_state = Book.objects.get(pk=obj.pk)
                    books_on_loan = old_book_state.quantity_total - old_book_state.quantity_available
                except Book.DoesNotExist:
                    pass # Бул болбошу керек

            new_total = form.cleaned_data['quantity_total']
            if new_total < books_on_loan:
                # Ката берүү же available'ды тууралоо
                # Бул жерде колдонуучуга билдирүү көрсөтүү кыйын, андыктан этият болуу керек
                obj.quantity_available = 0 # Мисалы, эң аз дегенде 0
                # messages.error(request, "Жаңы жалпы сан берилген китептерден аз боло албайт!") # Бул иштебеши мүмкүн
            else:
                obj.quantity_available = new_total - books_on_loan
        elif not obj.pk: # Жаңы китеп
            obj.quantity_available = obj.quantity_total

        super().save_model(request, obj, form, change)


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_id', 'user_type', 'get_user_type_display')
    search_fields = ('name', 'user_id')
    list_filter = ('user_type',)

    def get_user_type_display(self, obj):
        return obj.get_user_type_display()
    get_user_type_display.short_description = 'Колдонуучунун тиби'


@admin.register(LoanRecord)
class LoanRecordAdmin(admin.ModelAdmin):
    list_display = ('book', 'borrower', 'loan_date', 'due_date', 'return_date', 'is_overdue_admin')
    list_filter = ('loan_date', 'due_date', 'return_date', ('book', admin.RelatedOnlyFieldListFilter))
    search_fields = ('book__title', 'borrower__name', 'book__isbn', 'borrower__user_id')
    readonly_fields = ('is_overdue_admin',)
    autocomplete_fields = ['book', 'borrower'] # Чоң маалыматтар үчүн издөө жеңилдейт

    def is_overdue_admin(self, obj):
        return obj.is_overdue
    is_overdue_admin.boolean = True # Галочка/крестик менен көрсөтөт
    is_overdue_admin.short_description = 'Мөөнөтү өткөнбү?'

    def save_model(self, request, obj, form, change):
        # Админка аркылуу LoanRecord сакталганда китептин санын жана loan_count'ту жаңыртуу
        book = obj.book
        old_instance = None
        if obj.pk: # Эгер объект өзгөртүлүп жатса
            try:
                old_instance = LoanRecord.objects.get(pk=obj.pk)
            except LoanRecord.DoesNotExist:
                pass # Бул болбошу керек

        super().save_model(request, obj, form, change) # Адегенде сактоо

        if not old_instance: # Жаңы LoanRecord түзүлдү
            Book.objects.filter(pk=book.pk).update(
                quantity_available=F('quantity_available') - 1,
                loan_count=F('loan_count') + 1
            )
        elif old_instance and old_instance.return_date is None and obj.return_date is not None:
            # Китеп кайтарылды (return_date коюлду)
            Book.objects.filter(pk=book.pk).update(quantity_available=F('quantity_available') + 1)
        elif old_instance and old_instance.return_date is not None and obj.return_date is None:
            # Китеп кайрадан "карызга алынды" (return_date алынып салынды)
             Book.objects.filter(pk=book.pk).update(quantity_available=F('quantity_available') - 1)
        
        book.refresh_from_db() # Обновляем состояние книги из базы

    def delete_model(self, request, obj):
        # Эгер активдүү карыз өчүрүлсө, китептин санын калыбына келтирүү
        if obj.return_date is None:
            book = obj.book
            Book.objects.filter(pk=book.pk).update(quantity_available=F('quantity_available') + 1)
            # loan_count'ту азайтуу талаштуу, анткени китеп бир жолу алынган
            book.refresh_from_db()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.return_date is None:
                book = obj.book
                Book.objects.filter(pk=book.pk).update(quantity_available=F('quantity_available') + 1)
                book.refresh_from_db()
        super().delete_queryset(request, queryset)