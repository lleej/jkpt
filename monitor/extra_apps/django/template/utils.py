import functools
from collections import Counter, OrderedDict
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.module_loading import import_string


class InvalidTemplateEngineError(ImproperlyConfigured):
    pass


class EngineHandler:
    """
    保存项目配置文件中的settings.TEMPLATE配置信息
    该信息是模板引擎的配置信息
    该对象，在django.template.__init__.py中进行了实例化，也就是说是一个单例对象
    属性：
    1. _templates. 构造函数传入参数 或者 settings.TEMPLATE
    2. templates. 可用的所有TEMPLATE的配置信息
    3. all. 返回所有模板对象实例数组
    """
    def __init__(self, templates=None):
        """
        templates is an optional list of template engine definitions
        (structured like settings.TEMPLATES).
        """
        self._templates = templates
        # 初始化
        # 在 __getitem__ 读取时进行赋值
        self._engines = {}

    @cached_property
    def templates(self):
        """
        返回已安装的所有可用模板
        例如：
        templates的结构，在settings.TEMPLATE原有结构基础上，添加了'NAME'
        OrderedDict([(
            'django',
            {
                'NAME': 'django',
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(BASE_DIR, 'templates')],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'django.template.context_processors.media',
                    ],
                },
            }
        )])
        :return: templates OrderedDict实例
        """
        # 如果初始化没有传入templates，则使用配置文件中的设置
        # 因为在Template包的初始化'__init__.py'中，创建了单例 engines = EngineHandler()
        # 所以，肯定是没有传入参数的，也就是说，其实是使用了配置参数中的设置
        if self._templates is None:
            self._templates = settings.TEMPLATES
        # 作为输出的临时变量
        templates = OrderedDict()
        # 用于判断是否有重复导入模板的临时变量
        backend_names = []
        # 遍历settings.TEMPLATE中的配置项，默认只有一个
        for tpl in self._templates:
            try:
                # This will raise an exception if 'BACKEND' doesn't exist or
                # isn't a string containing at least one dot.
                # settings.TEMPLATES 中的 'BACKEND'的默认值为 'django.template.backends.django.DjangoTemplates'
                # rsplit('.', 2)处理完后，是['django.template.backends', 'django', 'DjangoTemplates']
                # [-2]对应的就是'django'，即 default_name = 'django'
                default_name = tpl['BACKEND'].rsplit('.', 2)[-2]
            except Exception:
                invalid_backend = tpl.get('BACKEND', '<not defined>')
                raise ImproperlyConfigured(
                    "Invalid BACKEND for a template engine: {}. Check "
                    "your TEMPLATES setting.".format(invalid_backend))

            # 在原有TEMPLATE结构的基础上，增加了'NAME'属性
            # 后面的**tpl是用来覆盖前面的默认项的，保证不会出现结构不符的情况
            tpl = {
                'NAME': default_name,
                'DIRS': [],
                'APP_DIRS': False,
                'OPTIONS': {},
                **tpl,
            }

            templates[tpl['NAME']] = tpl
            backend_names.append(tpl['NAME'])

        # 如果配置的模板有重复，则触发异常
        counts = Counter(backend_names)
        duplicates = [alias for alias, count in counts.most_common() if count > 1]
        if duplicates:
            raise ImproperlyConfigured(
                "Template engine aliases aren't unique, duplicates: {}. "
                "Set a unique NAME for each engine in settings.TEMPLATES."
                .format(", ".join(duplicates)))

        # 返回的是配置信息
        return templates

    def __getitem__(self, alias):
        """
        将自身转换为一个迭代对象
        :param alias: 模板引擎的名称，即OrderedDict中的key值
        :return: 模板引擎的实例
        """
        try:
            # _engines默认为{}
            # 当执行该函数，并成功取出一个Template时，将导入该模板模块
            # 然后将模板实例添加到_engines中，key值为alias
            return self._engines[alias]
        except KeyError:
            try:
                # 从templates属性中取出
                params = self.templates[alias]
            except KeyError:
                raise InvalidTemplateEngineError(
                    "Could not find config for '{}' "
                    "in settings.TEMPLATES".format(alias))

            # If importing or initializing the backend raises an exception,
            # self._engines[alias] isn't set and this code may get executed
            # again, so we must preserve the original params. See #24265.
            params = params.copy()
            backend = params.pop('BACKEND')
            # 导入Backend模块，注意入参是一个实际的类，返回该类
            engine_cls = import_string(backend)
            engine = engine_cls(params)

            self._engines[alias] = engine
            return engine

    def __iter__(self):
        """
        把OrderedDict转换为迭代对象
        :return: templates中所有key值的迭代对象
        """
        # iter(OrderdDict()) 把OrderedDict的key值取出，作为迭代的值
        # 调用templates()方法
        return iter(self.templates)

    def all(self):
        """
        返回所有的可以使用的模板
        :return:
        """
        # 这一句话很有意思，处理非常巧妙
        # 1. for alias in self 使用了self的迭代器，也就是要调用__iter__函数
        # 所以取出的alias应该是templates()返回的配置列表的Dict的Key，例如:django
        # 2. self[alias] 使用了取出成员的特性，也就是要调用 __getitem__ 函数
        # 返回的是可以使用的模板引擎的实例
        # 最终返回一个列表表达式
        return [self[alias] for alias in self]


@functools.lru_cache()
def get_app_template_dirs(dirname):
    """
    Return an iterable of paths of directories to load app templates from.

    dirname is the name of the subdirectory containing templates inside
    installed applications.
    """
    # 注意：Path(app_config.path) / dirname 的用法
    # Path是原生pathlib.py中的类，支持 / 连接
    template_dirs = [
        str(Path(app_config.path) / dirname)
        for app_config in apps.get_app_configs()
        if app_config.path and (Path(app_config.path) / dirname).is_dir()
    ]
    # Immutable return value because it will be cached and shared by callers.
    return tuple(template_dirs)
