from datetime import datetime

from django.db import models

"""
设备通讯参数
"""


class CommInfo(models.Model):
    """
    设备的通讯参数
    """
    param = models.CharField(default="", max_length=255, verbose_name="通讯参数")
    desc = models.CharField(default="", max_length=255, verbose_name="参数描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "通讯参数"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.param