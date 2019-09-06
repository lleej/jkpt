from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from common.models import Highway, Section
from common.serializers import HighwaySerializer, SectionSerializer

from utils.pagination import CustomPagination


class HighwayViewSet(viewsets.ModelViewSet):
    # 是一个queryset 不是 model
    queryset = Highway.objects.all()
    serializer_class = HighwaySerializer
    pagination_class = CustomPagination
    # 可以筛选的字段，筛选参数为 字段名=内容
    # 筛选是：内容必须完全匹配字段的值
    filterset_fields = ['code', 'name']
    # 可以搜索的字段，搜索参数为 search=内容
    # 搜索是：内容可以完全/部分匹配所有在list中指定的字段
    search_fields = ['name', 'desc']
    # 可以排序的字段，排序参数为 ordering=字段名
    ordering_fields = ['code', 'mileage']
    # 默认排序字段
    ordering = ['code']

    @action(detail=True, methods=['get'])
    def sections(self, request, pk=None):
        """
        查询某个高速包含的全部路段
        :param request:
        :return: 路段集合
        """
        highway = self.get_object()
        section_queryset = Section.objects.filter(pk=highway.pk)
        section_serializer = SectionSerializer(section_queryset, many=True)
        return self.get_paginated_response(section_serializer.data)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    pagination_class = CustomPagination

