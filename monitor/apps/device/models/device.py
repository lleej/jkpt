from datetime import datetime
from django.db import models

from common.models import Department, Highway
from .devicetype import DeviceType
from .comm import CommInfo


class Device(models.Model):
    """
    设备
    """
    name = models.CharField(default="", max_length=100, verbose_name="设备名称", help_text="请输入设备名")
    code = models.CharField(default="", max_length=100, verbose_name="设备编码", help_text="请输入设备编码")
    device_type = models.ForeignKey(DeviceType, null=True, blank=True, verbose_name="设备类型",
                                    related_name="devices", on_delete=models.SET_NULL)
    Highway = models.ForeignKey(Highway, on_delete=models.SET_NULL, verbose_name="所属高速", null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, verbose_name="管理单位", null=True, blank=True)
    stake_mark = models.CharField(default="", max_length=20, verbose_name="桩号", help_text="请输入桩号")
    comm_info = models.ForeignKey(CommInfo, on_delete=models.SET_NULL, verbose_name="通讯参数", null=True, blank=True)
    # direction = models.
    # 以下是显示相关
    # 设备在地图上的显示坐标 格式: x,y
    coordinate = models.CharField(default="", max_length=20, verbose_name="显示坐标")
    longitude = models.FloatField(default=0.0, verbose_name="经度")
    latitude = models.FloatField(default=0.0, verbose_name="纬度")
