from rest_framework import serializers

from common.models import Highway, Section


"""
Highway.py中模型的序列化
Highway 和 Section
"""


class SectionSerializer(serializers.ModelSerializer):
    """
    路段模型的序列化
    """
    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = Section
        fields = '__all__'


class HighwaySerializer(serializers.ModelSerializer):
    """
    高速公路模型的序列化
    """
    # 解决了序列化日期时间，默认格式为: yyyy-mm-ddThh:mm:ss.xxxxxZ 的问题
    # 但是，这样会导致序列化字段的顺序发生变化，在序列化类中指定的字段会出现在其他字段的前面(id主键的后面)
    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    sections = SectionSerializer(many=True)

    class Meta:
        model = Highway
        fields = '__all__'



