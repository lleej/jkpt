import functools
from importlib import import_module
from inspect import getfullargspec

from django.utils.html import conditional_escape
from django.utils.itercompat import is_iterable

from .base import Node, Template, token_kwargs
from .exceptions import TemplateSyntaxError


class InvalidTemplateLibrary(Exception):
    pass


"""
类型：Library
作用：保存模块中Tag和Filter的处理函数
Library 用于 Engine 中标记的处理函数
1. 一个模板标签模块中包含多个Tag和Filte的处理函数
2. 将这些处理函数注册到Library中，便于统一管理
3. 每个模板标签模块必须有唯一的一个实例，且命名为: register 该实例必须在所有装饰器函数调用的前面完成

属性：
1. tags. 存储本模块中所有 tag 装饰器装饰的处理函数
2. filters. 存储本模块中所有 filter 装饰器装饰的处理函数

方法：
1. filter. 装饰器，装饰过滤器处理函数，用法是 register.filter
2. tag. 装饰器，装饰语法标记处理函数，用法是 register.tag 
"""


class Library:
    """
    A class for registering template tags and filters. Compiled filter and
    template tag functions are stored in the filters and tags attributes.
    The filter, simple_tag, and inclusion_tag methods provide a convenient
    way to register callables as tags.
    """
    def __init__(self):
        self.filters = {}
        self.tags = {}

    def tag(self, name=None, compile_function=None):
        """
        tag 装饰器
        :param name: 标识名称，目的是适应一些关键字名，例如：if for 等不能作为函数名
        :param compile_function: 编译 tag 的处理函数
        :return: 传入的编译函数
        """
        # tag 装饰器对装饰器的所有书写格式都进行了处理，可以作为理解装饰器用法的很好的案例
        # 共考虑到装饰器的三种书写格式
        if name is None and compile_function is None:
            # 1. @register.tag()
            # 解释：
            # a. 调用tag()函数，传入的参数都是默认值
            # b. 返回函数tag_function的引用，注意不是调用函数的结果
            # c. 执行tag_function，被包装的函数作为其参数
            return self.tag_function
        elif name is not None and compile_function is None:
            if callable(name):
                # 2. @register.tag
                # 解释
                # a. 不带括号，则被装饰的函数作为其参数被传入
                # b. 调用 tag_function 将被装饰的函数 传入
                return self.tag_function(name)
            else:
                # 3. @register.tag('somename') or @register.tag(name='somename')
                # 解释：
                # a. 只传入tag的名称。一般是用于tag名称是关键字的情况，如: if for 。这时tag名称和对应的处理函数名称不一致
                # b. 返回函数dec，函数是一个闭包，其中使用了本次传入的 tag name
                # c. 执行dec函数，将被装饰的函数作为参数，迭代调用tag方法，这时name和func都有对应的值
                def dec(func):
                    return self.tag(name, func)
                return dec
        elif name is not None and compile_function is not None:
            # 4. register.tag('somename', somefunc)
            # 解释：
            # a. 不是通常装饰器的书写格式
            # b. 可以看做是一般的函数调用, somefunc 指函数名
            self.tags[name] = compile_function
            return compile_function
        else:
            raise ValueError(
                "Unsupported arguments to Library.tag: (%r, %r)" %
                (name, compile_function),
            )

    def tag_function(self, func):
        self.tags[getattr(func, "_decorated_function", func).__name__] = func
        return func

    def filter(self, name=None, filter_func=None, **flags):
        """
        filter 装饰器
        给过滤器函数添加 _filter_name = name 属性
        如果flags include ('expects_localtime', 'is_safe', 'needs_autoescape')
        给过滤器函数添加相应的属性
        :param name: 过滤器名称，目的是适应一些关键字名不能作为函数名
        :param filter_func: filter 的处理函数
        :param flags: 关键字参数
        :return: 传入的过滤器函数

        Register a callable as a template filter. Example:

        @register.filter
        def lower(value):
            return value.lower()
        """
        # filter 装饰器对装饰器的所有书写格式都进行了处理，可以作为理解装饰器用法的很好的案例
        # 共考虑到装饰器的三种书写格式
        if name is None and filter_func is None:
            # 1. @register.filter()
            # 解释：
            # a. 调用 filter() 函数，传入的参数都是默认值
            # b. 返回函数 dec 的引用，注意不是调用函数的结果
            # c. 因为 filter_function 需要 flags 参数，所以这里采用闭包，现将 flags 传入
            # d. 执行 filter_function，被包装的函数作为其参数func
            # e. filter_function 会重入 filter 所有的参数都配齐
            def dec(func):
                return self.filter_function(func, **flags)
            return dec
        elif name is not None and filter_func is None:
            if callable(name):
                # 2. @register.filter
                # 解释：
                # a. 不带括号，则被装饰的函数作为其参数被传入
                # b. 执行 filter_function，func 和 flags 都传入
                # c. filter_function 会重入 filter 所有的参数都配齐
                return self.filter_function(name, **flags)
            else:
                # 3. @register.filter('somename') or @register.filter(name='somename')
                # 解释：
                # a. 只传入 filter 的名称。一般是用于 filter 名称是关键字的情况。这时 filter 名称和对应的处理函数名称不一致
                # b. 返回函数dec，函数是一个闭包，其中使用了本次传入的 filter name 和 flags
                # c. 执行dec函数，将被装饰的函数作为参数，迭代调用 filter 方法，这时 name 和 func 都有对应的值
                def dec(func):
                    return self.filter(name, func, **flags)
                return dec
        elif name is not None and filter_func is not None:
            # 4. register.filter('somename', somefunc)
            # 解释：
            # a. 不是通常装饰器的书写格式
            # b. 可以看做是一般的函数调用, somefunc 指函数名
            self.filters[name] = filter_func
            for attr in ('expects_localtime', 'is_safe', 'needs_autoescape'):
                if attr in flags:
                    value = flags[attr]
                    # set the flag on the filter for FilterExpression.resolve
                    setattr(filter_func, attr, value)
                    # set the flag on the innermost decorated function
                    # for decorators that need it, e.g. stringfilter
                    if hasattr(filter_func, "_decorated_function"):
                        setattr(filter_func._decorated_function, attr, value)
            # 给过滤器处理函数添加 _filter_name 属性
            filter_func._filter_name = name
            return filter_func
        else:
            raise ValueError(
                "Unsupported arguments to Library.filter: (%r, %r)" %
                (name, filter_func),
            )

    def filter_function(self, func, **flags):
        name = getattr(func, "_decorated_function", func).__name__
        return self.filter(name, func, **flags)

    def simple_tag(self, func=None, takes_context=None, name=None):
        """
        注册一个 simple_tag 标记处理函数
        该函数可以不是 func(parser, token) 标准的函数，可以自定义入口参数
        一般用于需要传入在Token中写入的参数的处理函数
        该函数执行并返回一个 SimpleNode 节点对象
        :param takes_context boolean类型 表示 func 的第一个参数是否是 context

        Register a callable as a compiled template tag. Example:

        @register.simple_tag
        def hello(*args, **kwargs):
            return 'world'
        """
        def dec(func):
            """
            simple_tag装饰器注册 tag 的处理函数
            把被包装函数，封装到一个SimpleNode对象中，将Token中的参数进行处理后，传入SimpleNode实例中，以便于被包装函数执行
            :param func: 被包装函数
            :return: 无所谓了
            """
            # 分解出被包装函数的参数和默认值
            params, varargs, varkw, defaults, kwonly, kwonly_defaults, _ = getfullargspec(func)
            function_name = (name or getattr(func, '_decorated_function', func).__name__)

            @functools.wraps(func)
            def compile_func(parser, token):
                """
                tag的编译函数必须采用这种格式的入参
                :param parser: 语法解析器
                :param token: Token实例
                :return: 返回一个 SimpleNode实例
                """
                # 提取Token中的所有变量
                bits = token.split_contents()[1:]
                target_var = None
                # 如果有as语句，则处理结果要放到 as 后面的变量中
                if len(bits) >= 2 and bits[-2] == 'as':
                    target_var = bits[-1]
                    bits = bits[:-2]
                # 分析Token中的参数与处理函数的参数是否匹配
                # 将Token中的参数转换为FilterExpression()实例，保存到args中
                args, kwargs = parse_bits(
                    parser, bits, params, varargs, varkw, defaults,
                    kwonly, kwonly_defaults, takes_context, function_name,
                )
                # 创建一个Node节点并返回，这也是Tag编译函数的规则
                return SimpleNode(func, takes_context, args, kwargs, target_var)
            # 这句是关键，调用默认的 tag 注册，将处理函数注册到register中
            self.tag(function_name, compile_func)
            return func

        if func is None:
            # @register.simple_tag(...)
            return dec
        elif callable(func):
            # @register.simple_tag
            return dec(func)
        else:
            raise ValueError("Invalid arguments provided to simple_tag")

    def inclusion_tag(self, filename, func=None, takes_context=None, name=None):
        """
        Register a callable as an inclusion tag:

        @register.inclusion_tag('results.html')
        def show_results(poll):
            choices = poll.choice_set.all()
            return {'choices': choices}
        """
        def dec(func):
            params, varargs, varkw, defaults, kwonly, kwonly_defaults, _ = getfullargspec(func)
            function_name = (name or getattr(func, '_decorated_function', func).__name__)

            @functools.wraps(func)
            def compile_func(parser, token):
                bits = token.split_contents()[1:]
                args, kwargs = parse_bits(
                    parser, bits, params, varargs, varkw, defaults,
                    kwonly, kwonly_defaults, takes_context, function_name,
                )
                return InclusionNode(
                    func, takes_context, args, kwargs, filename,
                )
            self.tag(function_name, compile_func)
            return func
        return dec


class TagHelperNode(Node):
    """
    作为SimpleNode 和 InclusionNode 的基类
    保存实际的处理函数以及入口参数等信息

    Base class for tag helper nodes such as SimpleNode and InclusionNode.
    Manages the positional and keyword arguments to be passed to the decorated
    function.
    """
    def __init__(self, func, takes_context, args, kwargs):
        self.func = func
        self.takes_context = takes_context
        self.args = args
        self.kwargs = kwargs

    def get_resolved_arguments(self, context):
        """
        渲染参数变量的结果
        """
        resolved_args = [var.resolve(context) for var in self.args]
        if self.takes_context:
            resolved_args = [context] + resolved_args
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        return resolved_args, resolved_kwargs


class SimpleNode(TagHelperNode):

    def __init__(self, func, takes_context, args, kwargs, target_var):
        super().__init__(func, takes_context, args, kwargs)
        self.target_var = target_var

    def render(self, context):
        """
        节点渲染
        :param context: 上下文
        :return: 如果有target_var，则将渲染的结果放到context[target_var]中；否则返回渲染结果
        """
        # 处理参数
        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
        # 执行处理函数并返回渲染结果
        output = self.func(*resolved_args, **resolved_kwargs)
        if self.target_var is not None:
            context[self.target_var] = output
            return ''
        if context.autoescape:
            output = conditional_escape(output)
        return output


class InclusionNode(TagHelperNode):

    def __init__(self, func, takes_context, args, kwargs, filename):
        super().__init__(func, takes_context, args, kwargs)
        self.filename = filename

    def render(self, context):
        """
        Render the specified template and context. Cache the template object
        in render_context to avoid reparsing and loading when used in a for
        loop.
        """
        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
        _dict = self.func(*resolved_args, **resolved_kwargs)

        t = context.render_context.get(self)
        if t is None:
            if isinstance(self.filename, Template):
                t = self.filename
            elif isinstance(getattr(self.filename, 'template', None), Template):
                t = self.filename.template
            elif not isinstance(self.filename, str) and is_iterable(self.filename):
                t = context.template.engine.select_template(self.filename)
            else:
                t = context.template.engine.get_template(self.filename)
            context.render_context[self] = t
        new_context = context.new(_dict)
        # Copy across the CSRF token, if present, because inclusion tags are
        # often used for forms, and we need instructions for using CSRF
        # protection to be as simple as possible.
        csrf_token = context.get('csrf_token')
        if csrf_token is not None:
            new_context['csrf_token'] = csrf_token
        return t.render(new_context)


def parse_bits(parser, bits, params, varargs, varkw, defaults,
               kwonly, kwonly_defaults, takes_context, name):
    """
    解析 simple_tag 和 inclusion_tag 中的参数，并判断参数名称和数量 是否 与 处理函数 一致
    :param parser: Parser
    :param bits: list(str) Token中 tag 后面的参数列表 {% admin_list_filter cl spec %} 则为 ['cl', 'spec']
    :param params: list(str) 调用 getfullargspec(func) 返回的函数参数信息中的 位置参数和默认值参数
    :param varargs: list(str) 调用 getfullargspec(func) 返回的函数参数信息中的 可变参数 *
    :param varkw: list(str) 调用 getfullargspec(func) 返回的函数参数信息中的 可变关键字参数 **
    :param defaults list(str) 调用 getfullargspec(func) 返回的函数参数信息中的 参数默认值
    :param kwonly list(str) 调用 getfullargspec(func) 返回的函数参数信息中的 关键字参数 因为是定义所以只能是[]
    :param kwonly_defaults dict() 调用 getfullargspec(func) 返回的函数参数信息中的 关键字参数默认值 []
    :param takes_context boolean params是否包含'context'
    :param name str 处理函数的函数名 'admin_list_filter'

    Parse bits for template tag helpers simple_tag and inclusion_tag, in
    particular by detecting syntax errors and by extracting positional and
    keyword arguments.
    """
    # 如果使用 simple_tag 装饰器注册 tag 的处理函数时，提供了 takes_context=True 参数
    # 则必须保证 处理函数的第一个入口参数名必须是 context
    if takes_context:
        if params[0] == 'context':
            params = params[1:]
        else:
            raise TemplateSyntaxError(
                "'%s' is decorated with takes_context=True so it must "
                "have a first argument of 'context'" % name)
    # args kwargs 是返回的数据
    # args 中保存的是FilterExpression()实例
    args = []
    kwargs = {}
    # 拷贝函数参数名称列表到临时变量
    unhandled_params = list(params)
    unhandled_kwargs = [
        kwarg for kwarg in kwonly
        if not kwonly_defaults or kwarg not in kwonly_defaults
    ]
    # 循环处理 bits中的内容，也就是Token中的参数
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        # 判断是否是key=value格式
        # 不是kwarg是{}
        kwarg = token_kwargs([bit], parser)
        if kwarg:
            # 是key=value格式
            # The kwarg was successfully extracted
            param, value = kwarg.popitem()
            if param not in params and param not in unhandled_kwargs and varkw is None:
                # 不是有效的参数
                # An unexpected keyword argument was supplied
                raise TemplateSyntaxError(
                    "'%s' received unexpected keyword argument '%s'" %
                    (name, param))
            elif param in kwargs:
                # 关键字参数已经存在
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError(
                    "'%s' received multiple values for keyword argument '%s'" %
                    (name, param))
            else:
                # All good, record the keyword argument
                # 放置到kwargs临时变量中，等待返回
                kwargs[str(param)] = value
                if param in unhandled_params:
                    # 在位置和默认值参数中，删去
                    # If using the keyword syntax for a positional arg, then
                    # consume it.
                    unhandled_params.remove(param)
                elif param in unhandled_kwargs:
                    # 在关键字参数中，也删去
                    # Same for keyword-only arguments
                    unhandled_kwargs.remove(param)
        else:
            # 不是key=value格式
            if kwargs:
                # 位置参数在可变关键字参数后面，是不允许的
                raise TemplateSyntaxError(
                    "'%s' received some positional argument(s) after some "
                    "keyword argument(s)" % name)
            else:
                # Record the positional argument
                # 转换参数为FilterExpression()实例，并添加到args临时变量中，准备返回
                args.append(parser.compile_filter(bit))
                try:
                    # Consume from the list of expected positional arguments
                    unhandled_params.pop(0)
                except IndexError:
                    if varargs is None:
                        raise TemplateSyntaxError(
                            "'%s' received too many positional arguments" %
                            name)
    if defaults is not None:
        # 有默认值的参数，如果没有在 Token 中提供该参数，也是允许的
        # 把未处理的参数列表中，删除有默认值的个数
        # Consider the last n params handled, where n is the
        # number of defaults.
        unhandled_params = unhandled_params[:-len(defaults)]
    if unhandled_params or unhandled_kwargs:
        # 如果有剩余的参数，则表示Token中的参数不匹配
        # Some positional arguments were not supplied
        raise TemplateSyntaxError(
            "'%s' did not receive value(s) for the argument(s): %s" %
            (name, ", ".join("'%s'" % p for p in unhandled_params + unhandled_kwargs)))
    return args, kwargs


def import_library(name):
    """
    加载模板标签模块
    1. 先加载模块，使用Python原生的import_module
    2. 如果加载成功，则返回该模块中的register实例。该实例中保存着模块中声明的Tags和Filters的处理函数

    :param name: str 注册tag 和 filter 的模块
    :return register: Library 注册模块的Library实例

    Load a Library object from a template tag module.
    """
    try:
        module = import_module(name)
    except ImportError as e:
        raise InvalidTemplateLibrary(
            "Invalid template library specified. ImportError raised when "
            "trying to load '%s': %s" % (name, e)
        )
    try:
        return module.register
    except AttributeError:
        raise InvalidTemplateLibrary(
            "Module  %s does not have a variable named 'register'" % name,
        )
