# api/urls.py (DRF API endpoint'тер үчүн)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'librarians', views.LibrarianViewSet, basename='librarian')
router.register(r'books', views.BookViewSet, basename='book') # /api-v1/books/
router.register(r'borrowers', views.BorrowerViewSet, basename='borrower') # /api-v1/borrowers/
router.register(r'loans', views.LoanRecordViewSet, basename='loanrecord') # /api-v1/loans/

urlpatterns = [
    path('', include(router.urls)), # Роутерге катталган ViewSet'тер үчүн URL'дер
    # Отчеттор үчүн API endpoint'тер
    path('reports/most-popular-books/', views.ReportMostPopularBooksView.as_view(), name='report_api_most_popular'),
    path('reports/currently-loaned-count/', views.ReportCurrentlyLoanedCountView.as_view(), name='report_api_loaned_count'),
    path('reports/library-stats/', views.ReportLibraryStatsView.as_view(), name='report_api_library_stats'),
]