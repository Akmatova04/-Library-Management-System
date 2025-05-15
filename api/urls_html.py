# api/urls_html.py (HTML баракчалар үчүн URL'дер)

from django.urls import path
from . import views

urlpatterns = [
    path('books/', views.BookListHTMLView.as_view(), name='page_book_list'), # /app/books/
    path('books/add/', views.AddBookHTMLView.as_view(), name='page_add_book'), # /app/books/add/
    path('books/edit/<int:book_id>/', views.EditBookHTMLView.as_view(), name='page_edit_book'), # /app/books/edit/1/

    path('borrowers/', views.BorrowersListHTMLView.as_view(), name='page_borrowers_list'), # /app/borrowers/
    path('loans/', views.LoanListHTMLView.as_view(), name='page_loan_list'), # /app/loans/
]