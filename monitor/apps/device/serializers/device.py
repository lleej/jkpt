from rest_framework import serializers

from device.models import DeviceType


"""
Highway.py中模型的序列化
Highway 和 Section
"""


class DeviceTypeSerializer(serializers.ModelSerializer):
    """
    高速公路模型的序列化
    """
    class Meta:
        model = DeviceType
        fields = '__all__'


