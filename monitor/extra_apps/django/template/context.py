from contextlib import contextmanager
from copy import copy

# Hard-coded processor for easier use of CSRF protection.
_builtin_context_processors = ('django.template.context_processors.csrf',)


class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass


class ContextDict(dict):
    """
    为什么通过创建ContextDict实例的方式来向Context实例中添加数据呢？
    初步分析：是否作为临时性的环境变量，创建一个ContextDict实例，将临时处理的环境变量添加进来，使用with处理后，将添加的临时变量删除
    功能：
    1. 向传入的Context实例的字典中添加数据
    2. 提供了with 上下文的处理。不解的是，__exit__中将Context中环境变量数组中的最后一个变量删除？
    """
    def __init__(self, context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 把传入的变量添加到context中
        context.dicts.append(self)
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        # 从context中删除变量
        self.context.pop()


class BaseContext:
    """
    管理山下文的基类
    属性：
    dicts: list. 保存添加的环境变量信息，环境变量可以使任何类型
    注意：dicts[0] 也就是环境变量的第一个元素，一定是 {'True': True, 'False': False, 'None': None}
    因此，我们会注意到在代码中很多的拷贝都是[1:]，也就是说要去掉这个内置的环境变量元素
    至于这个环境变量元素的作用，还不得而知，可能是将值的字符串转换为类型值
    """
    def __init__(self, dict_=None):
        """
        构造函数
        :param dict_: Any 可以是任何类型的值，具体要看在模板文件中到底需要什么类型
        """
        # 加入内置的第一组环境变量
        self._reset_dicts(dict_)

    def _reset_dicts(self, value=None):
        """
        初始化环境变量
        1. 第一个元素是 {'True': True, 'False': False, 'None': None}
        2. 在后面加入 Value
        :param value: Any
        :return: None
        """
        builtins = {'True': True, 'False': False, 'None': None}
        self.dicts = [builtins]
        if value is not None:
            self.dicts.append(value)

    def __copy__(self):
        duplicate = copy(super())
        duplicate.dicts = self.dicts[:]
        return duplicate

    def __repr__(self):
        return repr(self.dicts)

    def __iter__(self):
        """
        注意：是反向迭代输出，不是正向的，从最后一个元素开始
        :return: dicts
        """
        return reversed(self.dicts)

    def push(self, *args, **kwargs):
        """
        加入新的环境变量
        :param args:
        :param kwargs:
        :return: ContextDict实例
        """
        dicts = []
        for d in args:
            if isinstance(d, BaseContext):
                dicts += d.dicts[1:]
            else:
                dicts.append(d)
        return ContextDict(self, *dicts, **kwargs)

    def pop(self):
        """
        删除最后一个环境变量
        :return: 删除的变量
        """
        # 必须保证内置的环境变量有效
        if len(self.dicts) == 1:
            raise ContextPopException
        return self.dicts.pop()

    def __setitem__(self, key, value):
        """
        向当前的环境变量中添加数据
        何为当前：dicts[-1]
        :param key:
        :param value:
        :return: None
        """
        "Set a variable in the current context"
        self.dicts[-1][key] = value

    def set_upward(self, key, value):
        """
        在dicts中的环境变量，下标越往后级别越高
        如果级别高的变量中有key，则更新该key的value
        否则，当前环境变量中加入该值
        Set a variable in one of the higher contexts if it exists there,
        otherwise in the current context.
        """
        # 取出当前环境变量
        context = self.dicts[-1]
        for d in reversed(self.dicts):
            if key in d:
                # 如果环境变量列表中，某个变量包含key，则更新该变量
                context = d
                break
        context[key] = value

    def __getitem__(self, key):
        """
        不管dicts中哪个变量包含key，有则返回，无则报异常
        :param key:
        :return: value
        """
        "Get a variable's value, starting at the current context and going upward"
        for d in reversed(self.dicts):
            if key in d:
                return d[key]
        raise KeyError(key)

    def __delitem__(self, key):
        """
        只从当前环境变量中删除key值
        :param key:
        :return: None
        """
        "Delete a variable from the current context"
        del self.dicts[-1][key]

    def __contains__(self, key):
        """只要dicts中的任何元素包含key，则返回True"""
        return any(key in d for d in self.dicts)

    def get(self, key, otherwise=None):
        """
        如果dicts中的元素中有key，则返回该key的值。注意从后向前查找
        如果没有该key，则返回otherwise作为默认值
        :param key:
        :param otherwise:
        :return: value or otherwise
        """
        for d in reversed(self.dicts):
            if key in d:
                return d[key]
        return otherwise

    def setdefault(self, key, default=None):
        """
        如果dicts中的元素包含key，则返回key的值
        否则，向当前元素中添加key=default
        :param key:
        :param default:
        :return: key的value or default
        """
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def new(self, values=None):
        """
        Return a new context with the same properties, but with only the
        values given in 'values' stored.
        """
        new_context = copy(self)
        new_context._reset_dicts(values)
        return new_context

    def flatten(self):
        """
        将dicts从list转换为dict类型
        有可能会覆盖相同的key
        Return self.dicts as one dictionary.
        """
        flat = {}
        for d in self.dicts:
            flat.update(d)
        return flat

    def __eq__(self, other):
        """
        Compare two contexts by comparing theirs 'dicts' attributes.
        """
        return (
            isinstance(other, BaseContext) and
            # because dictionaries can be put in different order
            # we have to flatten them like in templates
            self.flatten() == other.flatten()
        )


class Context(BaseContext):
    """
    变量上下文的容器
    """
    "A stack container for variable context"
    def __init__(self, dict_=None, autoescape=True, use_l10n=None, use_tz=None):
        self.autoescape = autoescape
        self.use_l10n = use_l10n
        self.use_tz = use_tz
        self.template_name = "unknown"
        self.render_context = RenderContext()
        # Set to the original template -- as opposed to extended or included
        # templates -- during rendering, see bind_template.
        self.template = None
        super().__init__(dict_)

    @contextmanager
    def bind_template(self, template):
        """
        上下文管理的模板绑定，语法 with xxx.bind_template(): xxx
        使用contextmanager装饰器，可以直接将一个函数转换为上下文管理器。另外的方法参见ContextDict中的__enter__和__exit__
        在函数中 yield 前面的语句在 执行 with 块中的代码前执行；后面的语句在 执行完 with 语句块中的代码后执行
        :param template: Template实例
        :return: None
        """
        if self.template is not None:
            raise RuntimeError("Context is already bound to a template")
        self.template = template
        try:
            yield
        finally:
            self.template = None

    def __copy__(self):
        duplicate = super().__copy__()
        duplicate.render_context = copy(self.render_context)
        return duplicate

    def update(self, other_dict):
        """
        添加其他的dicts
        :param other_dict: BaseContext OR dict
        :return: ContextDict实例
        """
        "Push other_dict to the stack of dictionaries in the Context"
        if not hasattr(other_dict, '__getitem__'):
            raise TypeError('other_dict must be a mapping (dictionary-like) object.')
        if isinstance(other_dict, BaseContext):
            other_dict = other_dict.dicts[1:].pop()
        return ContextDict(self, other_dict)


class RenderContext(BaseContext):
    """
    保存模板状态的上下文管理器

    A stack container for storing Template state.

    RenderContext simplifies the implementation of template Nodes by providing a
    safe place to store state between invocations of a node's `render` method.

    The RenderContext also provides scoping rules that are more sensible for
    'template local' variables. The render context stack is pushed before each
    template is rendered, creating a fresh scope with nothing in it. Name
    resolution fails if a variable is not found at the top of the RequestContext
    stack. Thus, variables are local to a specific template and don't affect the
    rendering of other templates as they would if they were stored in the normal
    template context.
    """
    template = None

    def __iter__(self):
        yield from self.dicts[-1]

    def __contains__(self, key):
        return key in self.dicts[-1]

    def get(self, key, otherwise=None):
        return self.dicts[-1].get(key, otherwise)

    def __getitem__(self, key):
        return self.dicts[-1][key]

    @contextmanager
    def push_state(self, template, isolated_context=True):
        initial = self.template
        self.template = template
        if isolated_context:
            self.push()
        try:
            yield
        finally:
            self.template = initial
            if isolated_context:
                self.pop()


class RequestContext(Context):
    """
    This subclass of template.Context automatically populates itself using
    the processors defined in the engine's configuration.
    Additional processors can be specified as a list of callables
    using the "processors" keyword argument.
    """
    def __init__(self, request, dict_=None, processors=None, use_l10n=None, use_tz=None, autoescape=True):
        super().__init__(dict_, use_l10n=use_l10n, use_tz=use_tz, autoescape=autoescape)
        self.request = request
        self._processors = () if processors is None else tuple(processors)
        self._processors_index = len(self.dicts)

        # placeholder for context processors output
        self.update({})

        # empty dict for any new modifications
        # (so that context processors don't overwrite them)
        self.update({})

    @contextmanager
    def bind_template(self, template):
        """
        绑定一个Template实例，目的是使用Template中的context_processor来处理HttpRequest，将处理结果添加到Context中
        :param template: Template实例
        :return: None
        """
        if self.template is not None:
            raise RuntimeError("Context is already bound to a template")

        self.template = template
        # Set context processors according to the template engine's settings.
        # 传入的template必须是一个Template实例，使用其引擎中的context_processor
        processors = (template.engine.template_context_processors +
                      self._processors)
        updates = {}
        for processor in processors:
            updates.update(processor(self.request))
        self.dicts[self._processors_index] = updates

        try:
            yield
        finally:
            self.template = None
            # Unset context processors.
            self.dicts[self._processors_index] = {}

    def new(self, values=None):
        new_context = super().new(values)
        # This is for backwards-compatibility: RequestContexts created via
        # Context.new don't include values from context processors.
        if hasattr(new_context, '_processors_index'):
            del new_context._processors_index
        return new_context


def make_context(context, request=None, **kwargs):
    """
    基于传入的 dict 和 HttpRequest 创建 Context 实例
    1. 如果没有提供 request 参数，则创建 Context 实例
    2. 如果提供 request 参数，则创建 RequestContext 实例
    Create a suitable Context from a plain dict and optionally an HttpRequest.
    """
    if context is not None and not isinstance(context, dict):
        raise TypeError('context must be a dict rather than %s.' % context.__class__.__name__)
    if request is None:
        context = Context(context, **kwargs)
    else:
        # The following pattern is required to ensure values from
        # context override those from template context processors.
        original_context = context
        context = RequestContext(request, **kwargs)
        if original_context:
            context.push(original_context)
    return context
