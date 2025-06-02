from rest_framework.pagination import PageNumberPagination


class RecipePagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 30


class UserPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class LimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
