from rest_framework import viewsets

from device.models import DeviceType
from device.serializers import DeviceTypeSerializer

from utils.pagination import CustomPagination


class DeviceTypeViewSet(viewsets.ModelViewSet):
    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer
    pagination_class = CustomPagination

