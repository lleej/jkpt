from datetime import datetime
from django.db import models


class DeviceType(models.Model):
    """
    设备类型
    """
    # 注意CharField 和 TextField 类型，最好不要设置 null=True，这样在空时就有两种状态Null和空串
    # 因此，CharField 最好指定默认值为""
    name = models.CharField(max_length=30, default="", verbose_name="类型名称", help_text="请输入类型名称")
    code = models.CharField(max_length=30, default="", verbose_name="类型代码", help_text="请输入类型代码")
    desc = models.CharField(max_length=200, default="", verbose_name="类型描述", help_text="请输入类型描述")
    parent = models.ForeignKey("self", null=True, blank=True, verbose_name="父级类型", help_text="请选择父级类型",
                               related_name="sub_types", on_delete=models.CASCADE)
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "设备类型"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
