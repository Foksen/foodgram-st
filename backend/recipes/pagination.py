from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class RecipePagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 30

    def get_page_size(self, request):
        try:
            limit = int(request.query_params.get(
                self.page_size_query_param, self.page_size
            ))
            if limit < 0:
                return self.page_size
            return min(limit, self.max_page_size)
        except (TypeError, ValueError):
            return self.page_size

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class UserPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class LimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
