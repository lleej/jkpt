import os
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import module_has_submodule

MODELS_MODULE_NAME = 'models'

"""
    通过分析AppConfig的初始化过程create()方法，可以得出以下结论
    
    结论一：AppConfig子类的命名以及所属的模块命名，没有硬性的规定
    1. 应用中声明的AppConfig子类不用定义为'[应用名]Config'，例如：Polls应用'PollsConfig'
    2. AppConfig子类所属的模块不必命名为apps.py，可以使用任何命名，当然django默认创建为apps.py
    3. 定义的XxxConfig类，必须是AppConfig的子类
    
    结论二：对于INSTALLED_APPS中的配置项，只能是二选一：
    1. '[应用名称]/[包名称]'
    2. AppConfig的完整路径名'[应用名].[模块名].XxxConfig'
    但绝对不能是其他的名称。例如：'[应用名].[模块名]'
    
    结论三：对于使用AppConfig完整路径名的情况，必须在类中设置以下属性
    1. name。必须是AppConfig所在的[应用]/[包]的名称，例如：'Polls'
    
    结论四：对于使用[应用名]/[包名]的情况，有两种可选情况
    1. 不定义应用的AppConfig子类，这种情况下，django将创建默认的AppConfig。个人理解：主要是少了ready()的钩子处理部分
    2. 定义了AppConfig的子类，则必须在「应用」/[包]的初始化文件'__init__.py'中设置default_app_config属性，该属性值
       必须是XxxConfig类的完整路径。例如：'Polls.apps.PollsConfig'
    
    结论五：在create()方法中，加载了[应用]/[包]模块，以及XxxConfig所在的模块
    例如：'django.contrib.admin'，加载了'django.contrib.admin'包的'__init__.py'模块，以及'django.contrib.admin.apps'模块


    class AppConfig分析
    
    保存应用的配置信息(apps.py中的AppConfig子类)以及应用的模型模块(models.py或者models包中的models.Model子类)
    要想遍历应用的所有数据模型(models.Model子类)，需要从apps实例中查找
    
    主要的属性和方法
    
    属性：
    1. apps 
    类型：Apps
    作用：apps实例的引用，apps实例是在registry.py中实例化的，全局唯一
    在Apps.populate()方法中赋值
    
    2. label
    类型：字符串
    作用：应用标签，可以在应用的AppConfig子类中设置，默认为应用的最后一段的名称，__init__中初始化。作为数组的索引使用
    label不能包含'.'
    举例：polls是一个应用，则为polls；django.contrib.admin则为admin
    
    3. models
    类型：OrderedDict
    作用：保存应用的数据模型的字典，一个应用会有多个Model对象。all_models[self.label]的引用
    初始化：在self.import_models中初始化，在Apps.populate方法中赋值
    注意：该变量的值是在Apps.register_model(self, app_label, model)方法中进行赋值，更确切的说是apps.app_models数组被赋值
    而'Apps.register_model'方法，是在'django.db.base.ModelBase'这个元类中的实例化方法'__new__'中调用的
    这么看django对象间耦合很重
    
    4. models_module
    类型：Module类型
    作用：保存应用的应用中的Models模块的实例。在self.import_models函数中赋值
    
    5. module
    类型：Module
    作用：应用的Root模块的实例，实例化对象时传入
    
    6. name
    类型：字符串
    作用：保存应用的名称，可用于查找，实例化对象时传入
    
    7. path
    类型：字符串
    作用：应用的文件系统路径。__init__中初始化
    
    8. verbose_name
    类型：字符串
    作用：应用的人性化描述，一般情况是中文含义，在AppConfig的子类中设置。在__init__中初始化
    举例：verbose_name = '投票'
    
    
    方法：
    1. create(cls, entry)
    非常重要的一个函数！！！，创建实例必须使用它
    类型：类方法 @classmethod
    作用：创建AppConfig
    参数：entry 是settings.py中INSTALLED_APPS中的各应用。可以是模块也可以是AppConfig的路径
    举例：AppConfig.create('polls.apps.PollsConfig') | AppConfig.create('django.contrib.admin') | AppConfig.create('polls')


    2. _path_from_module(self, module)
    类型：内部函数
    作用：从Modelue实例中读取文件系统位置
    参数：Module对象实例
    
    3. ready(self)
    类型：可重载函数
    作用：在应用被加载之前，需要初始化的工作，可以放在这里。例如：信号量/钩子的注册
    
    4. import_models(self)
    类型：内部函数
    作用：引入应用的Models模块，并给self.models_module变量赋值
    
    5. get_model(self, model_name, require_ready=True)
    类型：方法，返回模型(Model)实例
    作用：根据模型的名称，查找模型实例
    
    6. get_models(self, include_auto_create=False, include_swapped=False)
    类型：方法，返回模型(Model)实例的数组，是一个生成器yield
    作用：返回当前应用所有的Model实例，默认不包含自动创建(M2M)

"""


class AppConfig:
    """Class representing a Django application and its configuration."""

    def __init__(self, app_name, app_module):
        # Full Python path to the application e.g. 'django.contrib.admin'.
        self.name = app_name

        # Root module for the application e.g. <module 'django.contrib.admin'
        # from 'django/contrib/admin/__init__.py'>.
        self.module = app_module

        # Reference to the Apps registry that holds this AppConfig. Set by the
        # registry when it registers the AppConfig instance.
        self.apps = None

        # The following attributes could be defined at the class level in a
        # subclass, hence the test-and-set pattern.

        # Last component of the Python path to the application e.g. 'admin'.
        # This value must be unique across a Django project.
        if not hasattr(self, 'label'):
            self.label = app_name.rpartition(".")[2]

        # Human-readable name for the application e.g. "Admin".
        if not hasattr(self, 'verbose_name'):
            self.verbose_name = self.label.title()

        # Filesystem path to the application directory e.g.
        # '/path/to/django/contrib/admin'.
        if not hasattr(self, 'path'):
            self.path = self._path_from_module(app_module)

        # Module containing models e.g. <module 'django.contrib.admin.models'
        # from 'django/contrib/admin/models.py'>. Set by import_models().
        # None if the application doesn't have a models module.
        self.models_module = None

        # Mapping of lowercase model names to model classes. Initially set to
        # None to prevent accidental access before import_models() runs.
        self.models = None

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.label)

    def _path_from_module(self, module):
        """Attempt to determine app's filesystem path from its module."""
        # See #21874 for extended discussion of the behavior of this method in
        # various cases.
        # Convert paths to list because Python's _NamespacePath doesn't support
        # indexing.
        paths = list(getattr(module, '__path__', []))
        if len(paths) != 1:
            filename = getattr(module, '__file__', None)
            if filename is not None:
                paths = [os.path.dirname(filename)]
            else:
                # For unknown reasons, sometimes the list returned by __path__
                # contains duplicates that must be removed (#25246).
                paths = list(set(paths))
        if len(paths) > 1:
            raise ImproperlyConfigured(
                "The app module %r has multiple filesystem locations (%r); "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % (module, paths))
        elif not paths:
            raise ImproperlyConfigured(
                "The app module %r has no filesystem location, "
                "you must configure this app with an AppConfig subclass "
                "with a 'path' class attribute." % (module,))
        return paths[0]

    @classmethod
    def create(cls, entry):
        """
        Factory that creates an app config from an entry in INSTALLED_APPS.
        创建APPConfig的静态函数，在Apps.populate中调用，通过遍历INSTALLED_APPS，依次创建
        """
        try:
            # If import_module succeeds, entry is a path to an app module,
            # which may specify an app config class with default_app_config.
            # Otherwise, entry is a path to an app config class or an error.
            # 如果传入的entry是一个模块的字符串表达，不是xxx.XxxConfig
            # 则可以直接加载模块，这一步不会出现异常
            module = import_module(entry)

        except ImportError:
            # Track that importing as an app module failed. If importing as an
            # app config class fails too, we'll trigger the ImportError again.
            module = None

            mod_path, _, cls_name = entry.rpartition('.')

            # Raise the original exception when entry cannot be a path to an
            # app config class.
            if not mod_path:
                raise

        else:
            # 进入到这里，表示模块加载成功，传入的entry是一个合法的模块的表达字符串
            try:
                # If this works, the app module specifies an app config class.
                # 如果该模块有自己的AppConfig子类，则在包的__init__.py中设置了default_app_config变量
                # django的模块都采用了这种模式
                # 将entry 替换为AppConfig的字符串标书
                entry = module.default_app_config
            except AttributeError:
                # Otherwise, it simply uses the default app config class.
                # 如果该模块没有自己的AppConfig子类，则创建默认的AppConfig实例
                # 直接返回，不执行下面的步骤
                return cls(entry, module)
            else:
                # 取出模块和AppConfig的类名
                mod_path, _, cls_name = entry.rpartition('.')

        # If we're reaching this point, we must attempt to load the app config
        # class located at <mod_path>.<cls_name>
        # 加载AppConfig所在的模块，默认是[应用].apps
        mod = import_module(mod_path)
        try:
            # 取出模块中的AppConfig类
            cls = getattr(mod, cls_name)
        except AttributeError:
            if module is None:
                # If importing as an app module failed, check if the module
                # contains any valid AppConfigs and show them as choices.
                # Otherwise, that error probably contains the most informative
                # traceback, so trigger it again.
                candidates = sorted(
                    repr(name) for name, candidate in mod.__dict__.items()
                    if isinstance(candidate, type) and
                    issubclass(candidate, AppConfig) and
                    candidate is not AppConfig
                )
                if candidates:
                    raise ImproperlyConfigured(
                        "'%s' does not contain a class '%s'. Choices are: %s."
                        % (mod_path, cls_name, ', '.join(candidates))
                    )
                import_module(entry)
            else:
                raise

        # Check for obvious errors. (This check prevents duck typing, but
        # it could be removed if it became a problem in practice.)
        # 判断该类是否是AppConfig的子类
        if not issubclass(cls, AppConfig):
            raise ImproperlyConfigured(
                "'%s' isn't a subclass of AppConfig." % entry)

        # Obtain app name here rather than in AppClass.__init__ to keep
        # all error checking for entries in INSTALLED_APPS in one place.
        try:
            # 自定义的AppConfig子类中必须设置name类属性
            # 该属性必须是所在应用的名称，注意不是apps的名称
            # 如django.contrib.admin.apps.AdminConfig 中设置的name为django.contrib.admin
            app_name = cls.name
        except AttributeError:
            raise ImproperlyConfigured(
                "'%s' must supply a name attribute." % entry)

        # Ensure app_name points to a valid module.
        # 确保app_name是一个有效的模块字符串表达
        # 如果传入的entry是[应用]，则该模块已经在前面加载过了
        # 如果传入的entry是[应用的AppConfig类]，则该模块在这里加载
        try:
            app_module = import_module(app_name)
        except ImportError:
            raise ImproperlyConfigured(
                "Cannot import '%s'. Check that '%s.%s.name' is correct." % (
                    app_name, mod_path, cls_name,
                )
            )

        # Entry is a path to an app config class.
        return cls(app_name, app_module)

    def get_model(self, model_name, require_ready=True):
        """
        Return the model with the given case-insensitive model_name.

        Raise LookupError if no model exists with this name.
        """
        if require_ready:
            self.apps.check_models_ready()
        else:
            self.apps.check_apps_ready()
        try:
            return self.models[model_name.lower()]
        except KeyError:
            raise LookupError(
                "App '%s' doesn't have a '%s' model." % (self.label, model_name))

    def get_models(self, include_auto_created=False, include_swapped=False):
        """
        Return an iterable of models.

        By default, the following models aren't included:

        - auto-created models for many-to-many relations without
          an explicit intermediate table,
        - models that have been swapped out.

        Set the corresponding keyword argument to True to include such models.
        Keyword arguments aren't documented; they're a private API.
        """
        self.apps.check_models_ready()
        for model in self.models.values():
            if model._meta.auto_created and not include_auto_created:
                continue
            if model._meta.swapped and not include_swapped:
                continue
            yield model

    def import_models(self):
        # Dictionary of models for this app, primarily maintained in the
        # 'all_models' attribute of the Apps this AppConfig is attached to.

        # 由于apps.all_models是DefaultDict类型，当访问该字典中不存在的Key时，其将自动创建一个空键值
        # 因此，当访问self.apps.all_models[self.label]时，如果不存在，则自动创建一个空的字典项
        # 并将该字典项赋值给self.models属性
        self.models = self.apps.all_models[self.label]

        # Model模块的名称必须是'Models'
        if module_has_submodule(self.module, MODELS_MODULE_NAME):
            models_module_name = '%s.%s' % (self.name, MODELS_MODULE_NAME)
            # 导入Model模块后，创建Model类时(注意不是实例)，会调用元类django.db.base.ModelBase.__new__()方法
            # 在该方法中，会调用apps.register_model()方法，完成对apps.all_models属性的赋值
            self.models_module = import_module(models_module_name)

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
