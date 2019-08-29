import functools

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .base import Context, Template
from .context import _builtin_context_processors
from .exceptions import TemplateDoesNotExist
from .library import import_library

"""
类型：Engine
作用：通用的模板引擎
概念：
1. 模板引擎。指对模板中的tag 和 filter 进行定义的模块。其载体为：Library()的实例 register
在模板引擎模块中，所有的 tag 和 filter 处理函数，都注册到 register 实例中 
但是：在这里是放在backends中的，不清楚为什么？

有什么：
1. 引擎包含的处理 tag 和 filter 的库 register 实例
能做什么：
1. 根据模板文件名称，渲染出字符串的结果
2. 根据模板字符串，返回Template实例
3. 根据模板文件名称，返回Template实例
"""


class Engine:
    """
    属性：
    1. 传入属性
        1.1 dirs: list 模板文件存放的路径，在settings.TEMPLATE中设置
        1.2 app_dirs: boolean 是否查找安装应用中的templates目录
        1.3 context_processors
        1.4 debug: boolean 是否调试状态
        1.5 loaders
        1.6 string_if_invalid: str 无效的替代字符
        1.7 file_charset: str 字符集名称
        1.8 libraries: dict 可以使用的标记处理库模块 即有 register实例的模块，其中包含了对 tag 和 filter 的处理函数
        1.9 builtins: list 内置标记处理库模块
        1.10 autoescape: boolean 是否进行HTML转义，对于HTML页面必须进行转义
    2. 属性
        2.1 default_builtins: list 默认内置标记处理库模块 硬编码
        2.2 template_builtins: list 内置标记处理库模块的register实例
        2.3 template_libraries: dict 自定义标记处理库模块的register实例

    方法：
    1. from_string(template_mode) 基于模板字符串，创建此引擎的Template实例
    2. get_default() 返回第一个可以使用的DjangoTemplate类型的引擎对象，一般用于Template中没有指定engine属性的情况
    3. get_template(name) 根据模板文件的名称，返回django.template.Template 实例
    4. select_template(name_list) 给出一个模板文件的列表，返回第一个可用的模板文件的 django.template.Template 实例
    5. render_to_string(name, context) 给出一个模板文件名(列表)以及上下文，读取模板文件，并基于上下文渲染出结果，返回渲染后的字符串
    """
    default_builtins = [
        'django.template.defaulttags',
        'django.template.defaultfilters',
        'django.template.loader_tags',
    ]

    def __init__(self, dirs=None, app_dirs=False, context_processors=None,
                 debug=False, loaders=None, string_if_invalid='',
                 file_charset='utf-8', libraries=None, builtins=None, autoescape=True):
        if dirs is None:
            dirs = []
        if context_processors is None:
            context_processors = []
        if loaders is None:
            loaders = ['django.template.loaders.filesystem.Loader']
            if app_dirs:
                loaders += ['django.template.loaders.app_directories.Loader']
            if not debug:
                loaders = [('django.template.loaders.cached.Loader', loaders)]
        else:
            if app_dirs:
                raise ImproperlyConfigured(
                    "app_dirs must not be set when loaders is defined.")
        if libraries is None:
            libraries = {}
        if builtins is None:
            builtins = []

        self.dirs = dirs
        self.app_dirs = app_dirs
        self.autoescape = autoescape
        self.context_processors = context_processors
        self.debug = debug
        self.loaders = loaders
        self.string_if_invalid = string_if_invalid
        self.file_charset = file_charset
        self.libraries = libraries
        self.template_libraries = self.get_template_libraries(libraries)
        self.builtins = self.default_builtins + builtins
        self.template_builtins = self.get_template_builtins(self.builtins)

    @staticmethod
    @functools.lru_cache()
    def get_default():
        """
        Return the first DjangoTemplates backend that's configured, or raise
        ImproperlyConfigured if none are configured.

        This is required for preserving historical APIs that rely on a
        globally available, implicitly configured engine such as:

        >>> from django.template import Context, Template
        >>> template = Template("Hello {{ name }}!")
        >>> context = Context({'name': "world"})
        >>> template.render(context)
        'Hello world!'
        """
        # Since Engine is imported in django.template and since
        # DjangoTemplates is a wrapper around this Engine class,
        # local imports are required to avoid import loops.
        from django.template import engines
        from django.template.backends.django import DjangoTemplates
        for engine in engines.all():
            if isinstance(engine, DjangoTemplates):
                return engine.engine
        raise ImproperlyConfigured('No DjangoTemplates backend is configured.')

    @cached_property
    def template_context_processors(self):
        context_processors = _builtin_context_processors
        context_processors += tuple(self.context_processors)
        return tuple(import_string(path) for path in context_processors)

    def get_template_builtins(self, builtins):
        return [import_library(x) for x in builtins]

    def get_template_libraries(self, libraries):
        loaded = {}
        for name, path in libraries.items():
            loaded[name] = import_library(path)
        return loaded

    @cached_property
    def template_loaders(self):
        return self.get_template_loaders(self.loaders)

    def get_template_loaders(self, template_loaders):
        loaders = []
        for template_loader in template_loaders:
            loader = self.find_template_loader(template_loader)
            if loader is not None:
                loaders.append(loader)
        return loaders

    def find_template_loader(self, loader):
        if isinstance(loader, (tuple, list)):
            loader, *args = loader
        else:
            args = []

        if isinstance(loader, str):
            loader_class = import_string(loader)
            return loader_class(self, *args)
        else:
            raise ImproperlyConfigured(
                "Invalid value in template loaders configuration: %r" % loader)

    def find_template(self, name, dirs=None, skip=None):
        tried = []
        for loader in self.template_loaders:
            try:
                template = loader.get_template(name, skip=skip)
                return template, template.origin
            except TemplateDoesNotExist as e:
                tried.extend(e.tried)
        raise TemplateDoesNotExist(name, tried=tried)

    def from_string(self, template_code):
        """
        Return a compiled Template object for the given template code,
        handling template inheritance recursively.
        """
        return Template(template_code, engine=self)

    def get_template(self, template_name):
        """
        Return a compiled Template object for the given template name,
        handling template inheritance recursively.
        """
        template, origin = self.find_template(template_name)
        if not hasattr(template, 'render'):
            # template needs to be compiled
            template = Template(template, origin, template_name, engine=self)
        return template

    def render_to_string(self, template_name, context=None):
        """
        Render the template specified by template_name with the given context.
        For use in Django's test suite.
        """
        if isinstance(template_name, (list, tuple)):
            t = self.select_template(template_name)
        else:
            t = self.get_template(template_name)
        # Django < 1.8 accepted a Context in `context` even though that's
        # unintended. Preserve this ability but don't rewrap `context`.
        if isinstance(context, Context):
            return t.render(context)
        else:
            return t.render(Context(context))

    def select_template(self, template_name_list):
        """
        Given a list of template names, return the first that can be loaded.
        """
        if not template_name_list:
            raise TemplateDoesNotExist("No template names provided")
        not_found = []
        for template_name in template_name_list:
            try:
                return self.get_template(template_name)
            except TemplateDoesNotExist as exc:
                if exc.args[0] not in not_found:
                    not_found.append(exc.args[0])
                continue
        # If we get here, none of the templates could be loaded
        raise TemplateDoesNotExist(', '.join(not_found))
