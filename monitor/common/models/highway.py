from django.db import models

"""
1. 高速公路数据
2. 路段数据
3. 方向数据
"""


class Highway(models.Model):
    """
    高速公路
    """
    # 高速公路编号，如：G1 G2713 S1080等
    code = models.CharField(default="", max_length=20, unique=True, verbose_name="高速编号")
    name = models.CharField(default="", max_length=100, verbose_name="高速公路全称")
    desc = models.CharField(default="", max_length=255, verbose_name="高速公路描述")
    stake_mark_start = models.CharField(default="", max_length=20, verbose_name="起始桩号")
    stake_mark_end = models.CharField(default="", max_length=20, verbose_name="结束桩号")
    mileage = models.FloatField(default=0.0, verbose_name="里程数(公里)")
    # auto_now_add=True 当新增记录时，自动更新为系统时间。一般用于记录创建时间
    # auto_now=True 当保存记录时，自动更新为系统时间。一般用于记录修改时间
    # 注意：当设置以上两个任意一个时，同时设置属性：read_only=True
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")

    class Meta:
        verbose_name = "高速公路"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Section(models.Model):
    """
    高速公路路段
    """
    code = models.CharField(default="", max_length=20, verbose_name="路段编号")
    name = models.CharField(default="", max_length=100, verbose_name="路段全称")
    highway = models.ForeignKey(Highway, on_delete=models.CASCADE, related_name="sections", verbose_name="所属高速")
    line_num = models.IntegerField(default=4, verbose_name="车道数")
    stake_mark_start = models.CharField(default="", max_length=20, verbose_name="起始桩号")
    stake_mark_end = models.CharField(default="", max_length=20, verbose_name="结束桩号")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")

    class Meta:
        verbose_name = "高速路段"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

