from datetime import datetime

from django.db import models
from .highway import Highway

"""
高速公路的管理部门
1. 管理部门。包括省中心、片区中心、路段中心、隧道所，各省的管理模式不同，最多四级
2. 收费站
3. 隧道
4. 桥梁
5. 服务区
"""


class Department(models.Model):
    """
    高速公路管理部门
    """
    code = models.CharField(default="", max_length=20, verbose_name="部门编码")
    name = models.CharField(default="", max_length=100, verbose_name="部门名称")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="sub_departs", verbose_name="上级部门")
    tel = models.CharField(default="", max_length=20, verbose_name="部门电话")
    leader = models.CharField(default="", max_length=20, verbose_name="负责人")
    desc = models.CharField(default="", max_length=255, verbose_name="部门描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "管理部门"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Toll(models.Model):
    """
    高速公路收费站
    """
    CATEGORY = (
        (0, "匝道收费站"),
        (1, "省界收费站"),
    )

    code = models.CharField(default="", max_length=20, verbose_name="收费站编码")
    name = models.CharField(default="", max_length=100, verbose_name="收费站名称")
    highway = models.ForeignKey(Highway, on_delete=models.CASCADE, related_name="tolls", verbose_name="所属高速")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="tolls", verbose_name="所属部门")
    category = models.IntegerField(choices=CATEGORY, verbose_name="收费站类型")
    line_entry_num = models.IntegerField(default=0, verbose_name="入口车道数")
    line_exit_num = models.IntegerField(default=0, verbose_name="出口车道数")
    leader = models.CharField(default="", max_length=20, verbose_name="负责人")
    tel = models.CharField(default="", max_length=20, verbose_name="联系电话")
    stake_mark = models.CharField(default="", max_length=20, verbose_name="桩号")
    desc = models.CharField(default="", max_length=255, verbose_name="收费站描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "收费站"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Tunnel(models.Model):
    """
    高速公路隧道
    """
    CATEGORY = (
        (0, "短隧道 <=500M"),
        (1, "中长隧道 500~1000M"),
        (2, "长隧道 1000~3000M"),
        (3, "特长隧道 >3000M"),
    )

    code = models.CharField(default="", max_length=20, verbose_name="隧道编码")
    name = models.CharField(default="", max_length=100, verbose_name="隧道名称")
    highway = models.ForeignKey(Highway, on_delete=models.CASCADE, related_name="tunnels", verbose_name="所属高速")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="tunnels", verbose_name="所属部门")
    category = models.IntegerField(choices=CATEGORY, verbose_name="隧道类型")
    left_mileage = models.IntegerField(default=0, verbose_name="左洞长度")
    right_mileage = models.IntegerField(default=0, verbose_name="右洞长度")
    desc = models.CharField(default="", max_length=255, verbose_name="隧道描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "隧道"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Bridge(models.Model):
    """
    高速公路桥梁
    """
    CATEGORY = (
        (0, "小桥 8~30M"),
        (1, "中桥 30~100M"),
        (2, "大桥 100~1000M"),
        (3, "特大桥 >1000M"),
    )

    code = models.CharField(default="", max_length=20, verbose_name="桥梁编码")
    name = models.CharField(default="", max_length=100, verbose_name="桥梁名称")
    highway = models.ForeignKey(Highway, on_delete=models.CASCADE, related_name="bridges", verbose_name="所属高速")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="bridges", verbose_name="所属部门")
    category = models.IntegerField(choices=CATEGORY, verbose_name="桥梁类型")
    mileage = models.IntegerField(default=0, verbose_name="桥梁长度")
    desc = models.CharField(default="", max_length=255, verbose_name="桥梁描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "桥梁"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Service(models.Model):
    """
    高速公路服务区
    """
    code = models.CharField(default="", max_length=20, verbose_name="服务区编码")
    name = models.CharField(default="", max_length=100, verbose_name="服务区名称")
    highway = models.ForeignKey(Highway, on_delete=models.CASCADE, related_name="services", verbose_name="所属高速")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="services", verbose_name="所属部门")
    stake_mark = models.CharField(default="", max_length=20, verbose_name="桩号")
    desc = models.CharField(default="", max_length=255, verbose_name="服务区描述")
    created_time = models.DateTimeField(default=datetime.now, verbose_name="添加时间")

    class Meta:
        verbose_name = "服务区"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

