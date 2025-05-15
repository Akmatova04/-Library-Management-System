# api/serializers.py

from rest_framework import serializers
from .models import Librarian, Book, Borrower, LoanRecord
from django.utils import timezone
from datetime import timedelta

class LibrarianSerializer(serializers.ModelSerializer):
    photo_url = serializers.ImageField(source='photo', read_only=True) # Сүрөттүн URL'ин көрсөтүү үчүн

    class Meta:
        model = Librarian
        fields = ['id', 'name', 'employee_id', 'photo', 'photo_url', 'info']
        extra_kwargs = {
            'photo': {'write_only': True, 'required': False} # 'photo' талаасы жазуу үчүн, бирок окууда 'photo_url' колдонулат
        }


class BookSerializer(serializers.ModelSerializer):
    image_cover_url = serializers.ImageField(source='image_cover', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'isbn', 'year_published',
            'quantity_total', 'quantity_available', 'genre',
            'image_cover', 'image_cover_url', 'loan_count'
        ]
        read_only_fields = ['quantity_available', 'loan_count'] # Булар логика менен башкарылат
        extra_kwargs = {
            'image_cover': {'write_only': True, 'required': False}
        }

    def update(self, instance, validated_data):
        # Эгер quantity_total өзгөртүлсө, quantity_available дагы тууралоо
        new_quantity_total = validated_data.get('quantity_total', instance.quantity_total)
        
        if new_quantity_total != instance.quantity_total:
            books_on_loan = instance.quantity_total - instance.quantity_available
            if new_quantity_total < books_on_loan:
                raise serializers.ValidationError({
                    "quantity_total": f"Жаңы жалпы сан ({new_quantity_total}) учурда берилген китептердин санынан ({books_on_loan}) аз боло албайт."
                })
            instance.quantity_available = new_quantity_total - books_on_loan
        
        # Калган талааларды жаңыртуу
        instance.title = validated_data.get('title', instance.title)
        instance.author = validated_data.get('author', instance.author)
        instance.isbn = validated_data.get('isbn', instance.isbn) # ISBN өзгөртүүгө уруксат, бирок этият болуу керек
        instance.year_published = validated_data.get('year_published', instance.year_published)
        instance.genre = validated_data.get('genre', instance.genre)
        # image_cover өзүнчө иштетилет, эгер берилсе
        if 'image_cover' in validated_data:
            instance.image_cover = validated_data.get('image_cover', instance.image_cover)

        instance.quantity_total = new_quantity_total # quantity_total'ды сактоо
        instance.save()
        return instance


class BorrowerSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    class Meta:
        model = Borrower
        fields = ['id', 'user_id', 'name', 'user_type', 'user_type_display']


# LoanRecord үчүн толук маалымат менен
class LoanRecordDetailSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True) # Китептин толук маалыматы
    borrower = BorrowerSerializer(read_only=True) # Алуучунун толук маалыматы
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = LoanRecord
        fields = ['id', 'book', 'borrower', 'loan_date', 'due_date', 'return_date', 'is_overdue']

# LoanRecord түзүү жана жаңыртуу үчүн
class LoanRecordCreateSerializer(serializers.ModelSerializer):
    # ID аркылуу китеп жана карыз алуучуну көрсөтүү
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    borrower = serializers.PrimaryKeyRelatedField(queryset=Borrower.objects.all())

    class Meta:
        model = LoanRecord
        fields = ['id', 'book', 'borrower', 'due_date', 'return_date'] # loan_date автоматтык түрдө коюлат

    def validate_book(self, value):
        # Китеп берүүдө (жаңы жазуу түзүүдө)
        if not self.instance and value.quantity_available <= 0: # self.instance жок болсо, бул жаңы объект
            raise serializers.ValidationError(f"'{value.title}' китеби учурда жок.")
        return value

    def validate(self, data):
        book = data.get('book')
        borrower = data.get('borrower')
        
        # Жаңы карыз түзүп жатканда гана текшерүү
        if not self.instance:
             # Эгер бул колдонуучуда бул китеп кайтарыла элек болсо
            if LoanRecord.objects.filter(book=book, borrower=borrower, return_date__isnull=True).exists():
                raise serializers.ValidationError({
                    "non_field_errors": [f"'{borrower.name}' бул '{book.title}' китебин кайтара элек."]
                })
        
        # Эгер due_date берилбесе, демейки 14 күн
        if 'due_date' not in data or not data['due_date']:
            data['due_date'] = timezone.now().date() + timedelta(days=14)
        
        # Кайтаруу мөөнөтү берүү күнүнөн эрте болбошу керек
        loan_date = self.instance.loan_date if self.instance else timezone.now().date()
        if data.get('due_date') and data.get('due_date') < loan_date:
            raise serializers.ValidationError({"due_date": "Кайтаруу мөөнөтү берүү күнүнөн эрте боло албайт."})
            
        return data

    def create(self, validated_data):
        book = validated_data.get('book')
        loan_record = LoanRecord.objects.create(**validated_data)
        
        # Китептин санын азайтуу жана канча жолу алынганын көбөйтүү
        book.quantity_available -= 1
        book.loan_count += 1
        book.save(update_fields=['quantity_available', 'loan_count'])
        return loan_record

    def update(self, instance, validated_data):
        # Китеп кайтарылганда (return_date коюлганда)
        old_return_date = instance.return_date
        instance = super().update(instance, validated_data) # Адегенде жаңыртуу
        new_return_date = instance.return_date

        if old_return_date is None and new_return_date is not None:
            # Китеп кайтарылды
            book = instance.book
            book.quantity_available += 1
            book.save(update_fields=['quantity_available'])
        elif old_return_date is not None and new_return_date is None:
            # Китеп кайрадан алынды (ката менен кайтарылган деп белгиленсе)
            book = instance.book
            if book.quantity_available > 0:
                book.quantity_available -= 1
                book.save(update_fields=['quantity_available'])
            else: # Бул жагдай болбошу керек, бирок коопсуздук үчүн
                raise serializers.ValidationError({"return_date": "Китеп кайра берүү үчүн жеткиликтүү эмес."})
        return instance

# Китепти кайтаруу үчүн жөнөкөй сериализатор
class ReturnBookSerializer(serializers.Serializer):
    # loan_id менен кайтаруу дагы жакшы вариант болмок
    book_isbn = serializers.CharField(write_only=True)
    borrower_user_id = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            loan_record = LoanRecord.objects.get(
                book__isbn=data['book_isbn'],
                borrower__user_id=data['borrower_user_id'],
                return_date__isnull=True
            )
            data['loan_record_instance'] = loan_record
        except LoanRecord.DoesNotExist:
            raise serializers.ValidationError("Бул колдонуучуда бул китеп боюнча активдүү карыз табылган жок.")
        except LoanRecord.MultipleObjectsReturned:
            # Бул жагдай теориялык жактан болбошу керек, эгер логика туура болсо
            raise serializers.ValidationError("Бир нече активдүү карыз табылды. Администраторго кайрылыңыз.")
        return data