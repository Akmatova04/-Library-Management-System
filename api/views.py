# api/views.py

from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Sum, F
from django_filters.rest_framework import DjangoFilterBackend # Фильтрлөө үчүн
from rest_framework import parsers

from .models import Librarian, Book, Borrower, LoanRecord
from .serializers import (
    LibrarianSerializer, BookSerializer, BorrowerSerializer,
    LoanRecordDetailSerializer, LoanRecordCreateSerializer, ReturnBookSerializer
)

class LibrarianViewSet(viewsets.ModelViewSet):
    queryset = Librarian.objects.all().order_by('name')
    serializer_class = LibrarianSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser) # Файл жүктөө үчүн
    search_fields = ['name', 'employee_id']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all().order_by('title')
    serializer_class = BookSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser) # Файл жүктөө үчүн
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genre', 'author', 'year_published']
    search_fields = ['title', 'author', 'isbn', 'genre'] # Эмне боюнча издөө
    ordering_fields = ['title', 'author', 'year_published', 'loan_count'] # Эмне боюнча сорттоо


class BorrowerViewSet(viewsets.ModelViewSet):
    queryset = Borrower.objects.all().order_by('name')
    serializer_class = BorrowerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user_type']
    search_fields = ['name', 'user_id']


class LoanRecordViewSet(viewsets.ModelViewSet):
    queryset = LoanRecord.objects.select_related('book', 'borrower').all().order_by('-loan_date')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'book__isbn': ['exact'],
        'book__title': ['icontains'],
        'borrower__user_id': ['exact'],
        'borrower__name': ['icontains'],
        'due_date': ['exact', 'gte', 'lte'], # gte: >=, lte: <=
        'return_date': ['isnull'], # Активдүү карыздар үчүн (return_date__isnull=True)
        'is_overdue': ['exact'] # Бул үчүн filterset_class түзүү керек болушу мүмкүн
    }
    search_fields = ['book__title', 'borrower__name', 'book__isbn']
    ordering_fields = ['loan_date', 'due_date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LoanRecordCreateSerializer
        return LoanRecordDetailSerializer # list, retrieve үчүн

    # Китепти кайтаруу үчүн өзүнчө action
    @action(detail=False, methods=['post'], serializer_class=ReturnBookSerializer, url_path='return-book')
    def return_book(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            loan_record = serializer.validated_data['loan_record_instance']
            
            loan_record.return_date = timezone.now().date()
            loan_record.save() # Бул LoanRecordCreateSerializer.update() чакырат

            # Жаңыртылган LoanRecord'ду кайтаруу
            # Эскертүү: LoanRecordDetailSerializer колдонуп, толук маалыматты көрсөтсө болот
            return_serializer = LoanRecordDetailSerializer(loan_record, context={'request': request})
            return Response(return_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='active-loans')
    def active_loans(self, request):
        """Учурда берилген (кайтарыла элек) китептердин тизмеси."""
        active_loans_qs = self.get_queryset().filter(return_date__isnull=True)
        
        # Пагинацияны колдонуу
        page = self.paginate_queryset(active_loans_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(active_loans_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='overdue-loans')
    def overdue_loans(self, request):
        """Мөөнөтү өтүп кеткен китептердин тизмеси."""
        today = timezone.now().date()
        overdue_loans_qs = self.get_queryset().filter(return_date__isnull=True, due_date__lt=today)
        
        page = self.paginate_queryset(overdue_loans_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(overdue_loans_qs, many=True)
        return Response(serializer.data)

# --- Отчеттор үчүн Views ---
class ReportMostPopularBooksView(generics.ListAPIView):
    queryset = Book.objects.filter(loan_count__gt=0).order_by('-loan_count')[:10] # Топ 10
    serializer_class = BookSerializer
    # Бул жерде пагинацияны өчүрүп койсо болот, анткени топ 10 гана
    pagination_class = None 

class ReportCurrentlyLoanedCountView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        count = LoanRecord.objects.filter(return_date__isnull=True).count()
        return Response({"currently_loaned_books_count": count})

class ReportLibraryStatsView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        total_unique_books = Book.objects.count()
        total_book_copies_data = Book.objects.aggregate(total_copies=Sum('quantity_total'))
        total_available_copies_data = Book.objects.aggregate(available_copies=Sum('quantity_available'))
        
        total_book_copies = total_book_copies_data['total_copies'] or 0
        total_available_copies = total_available_copies_data['available_copies'] or 0
        
        return Response({
            "total_unique_book_titles": total_unique_books,
            "total_book_copies_in_library": total_book_copies,
            "total_available_copies_in_library": total_available_copies,
        })
    


# api/views.py
# ... (DRF ViewSet'тер жана башка импорттор)
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404 # get_object_or_404 кошуу
from .models import Book # Book моделин импорттоо

class BookListHTMLView(TemplateView):
    template_name = "api/book_list_page.html"

class AddBookHTMLView(TemplateView):
    template_name = "api/book_form_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Жаңы Китеп Кошуу"
        return context

class EditBookHTMLView(TemplateView):
    template_name = "api/book_form_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Бул жерде book_id'ни алып, аны контекстке кошсок болот,
        # бирок JavaScript аны URL'ден өзү алып жатат.
        # Эгер Django template'ине баштапкы маалыматтарды бергибиз келсе,
        # book = get_object_or_404(Book, pk=kwargs['book_id'])
        # context['book_data_json'] = serializers.BookSerializer(book).data # Мисалы
        context['form_title'] = "Китепти Оңдоо"
        return context

# Башка баракчалар үчүн да ушундай View'дерди түзсөңүз болот:
class BorrowersListHTMLView(TemplateView):
    template_name = "api/borrowers_list_page.html" # Бул файлды түзүү керек

class LoanListHTMLView(TemplateView):
    template_name = "api/loan_list_page.html" # Бул файлды түзүү керек

# Мисал катары, borrower_list_page.html (жөнөкөй)
# api/templates/api/borrowers_list_page.html
"""
{% extends "api/base.html" %}
{% block title %}Карыз Алуучулар{% endblock %}
{% block content %}
<h2>Карыз Алуучулардын Тизмеси</h2>
<div id="borrowerList">Жүктөлүүдө...</div>
{% endblock %}
{% block extra_scripts %}
<script>
    fetch('/api/borrowers/')
        .then(res => res.json())
        .then(data => {
            const listDiv = document.getElementById('borrowerList');
            listDiv.innerHTML = '';
            const ul = document.createElement('ul');
            ul.classList.add('book-list'); // Окшош стиль үчүн
            (data.results || data).forEach(b => {
                const li = document.createElement('li');
                li.classList.add('book-item'); // Окшош стиль үчүн
                li.innerHTML = `<div class="title">${b.name}</div><div>ID: ${b.user_id}</div><div>Тиби: ${b.user_type_display}</div>`;
                ul.appendChild(li);
            });
            listDiv.appendChild(ul);
        })
        .catch(err => {
            document.getElementById('borrowerList').innerHTML = '<p style="color:red;">Ката кетти.</p>';
            console.error(err);
        });
</script>
{% endblock %}
"""