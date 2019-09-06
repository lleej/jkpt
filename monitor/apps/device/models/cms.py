from django.db import models

from .device import Device

"""
情报板设备
"""


class CMSDevice(Device):
    """
    情报板设备
    """
    CATEGORY = (
        (0, "门架"),
        (1, "F型"),
        (2, "T型"),
    )

    category = models.IntegerField(choices=CATEGORY, verbose_name="设备型号", default=0)
    is_color = models.BooleanField(default=False, verbose_name="是否全彩")
    is_light = models.BooleanField(default=False, verbose_name="是否光带")
    width = models.IntegerField(default=0, verbose_name="像素宽度")
    height = models.IntegerField(default=0, verbose_name="像素高度")

    class Meta:
        verbose_name = "情报板设备"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
