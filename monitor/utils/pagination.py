from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

"""
项目自定义分页类
"""


class CustomPagination(PageNumberPagination):
    """
    自定义分页类
    """
    page_size = 10
    page_query_param = 'page_num'
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response(OrderedDict({
            'count': self.page.paginator.count,
            'pages': self.page.paginator.num_pages,
            'results': data
        }))
