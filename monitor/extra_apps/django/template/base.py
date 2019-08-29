"""
This is the Django template system.
这是django的模板系统，对符合规格的模板字符串进行预处理
处理过程如下：
1. input = read(TemplateFile)
2. Tokens = Lexer.tokenize(input)
3. Nodes = parser.parse(tokens)
4. output = Nodes.render(context)

主要对象说明
1. 词法解析器 Lexer
作用：根据模板语法，将模板字符串转换为标记(token)
核心：使用正则表达式，根据语法标记进行分割。仅分隔模板语法块，不对其中的逻辑和变量进行处理
函数：Lexer.tokenize()
输入：模板字符串，例如：{{ user_name }}
输出：token list

词法解析器使用的对象：
    1.1 TokenType(Enum)
    作用：Token类型的枚举类型
        TEXT = 0
        VAR = 1
        BLOCK = 2
        COMMENT = 3
    可以作为常量使用，但为了提高处理性能，尽量使用其对应的数字

    1.2 Token
    作用：从模板字符串中，分隔出的词法标记，主要用于存储原始标记内容
    属性：
    1. token_type: 类型 对应 TokenType类型，例如：TokenType.VAR 或者 1
    2. contents: 内容 原始标记的内容，例如：{{ user_name }} contents: user_name
    3. position: 位置 在当前行中的起始和结束位置，例如：(0, 30)
    4. lineno: 行号 根据 \n 字符数量判断，例如：2


2. 语法解析器 Parser
作用：编译语法标记(token)为Node对象
核心：采用自顶向下的递归处理，本模块中提供了基础的TextNode和VariableNode，其他类型的节点在defaulttags.py模块以及用户自定义的模块中
函数：parser.parse(parse_until)
参数：parse_untile 表示递归处理到哪个Token结束本次递归
输入：Token list
输出：NodeList()实例

语法解析器使用的对象：
    2.1 Variable 变量处理对象
    作用：
    1. 处理Token的contents，判断其内容是常量"xxx"，还是变量xxx.yyy.zzz
    1.1 一个Token的contents中，可以包含多个待处理的变量
    2. 基于提供的context环境，得到变量对应的值
    属性：
    1. var 保存原始token串
    2. literal 当var是常量时(以引号包裹)，保存到literal
    3. lookups 当var是变量时，保存到lookups。用'.'分割，对于对象来说分解为多个值，保存到tuple中
    4. translate 是否需要翻译('_(xxx)')，
    函数：resolve(context) 从context环境对象中取出变量的值，可以是对象、变量、无参方法
    输出：渲染后的结果

    2.2 FilterExpression 过滤器表达式对象
    作用：处理Token中Variable的内容，得到变量对象Variant以及过滤器列表filters
    1. FilterExpression 只处理变量token，因为需要基于context得到计算后的值，而且结果可以通过过滤器进行处理
    2. 一个FilterExpression 只能有一个Variable对象
    属性：
    1. token. token的content 字符串
    2. var. token中包含的变量，Variable实例
    2. filters. token中包含的过滤器列表，格式[(func, [(False, Variable), (True, Variable)]), ]
    函数：resolve(context) 会调用Variable的resolve()函数，然后调用过滤器处理函数
    输出：渲染后的结果

    2.3 Node 节点对象
    作用：对包含的子节点或者变量进行渲染
    说明：Node 是一个基类，提供了render()函数
    属性：
    1. token. 初始化为None，没有使用
    2. child_nodelists. 存放保存子节点的属性名称. 初始化为: ('nodelist',)
    3. must_be_first. Boolean类型，是否作为第一个节点渲染，初始化为：False
    函数：
    1. get_nodes_by_type(nodetype) 遍历节点以及子节点中nodetype的节点，并以list的形式返回。子类可以直接使用
    2. render(context) 渲染函数，子类必须重载之
    3. render_annotated(context) 当Debug开启时，输出有价值信息
    可以通过继承Node，实现对特定节点的渲染，例如：if for url等
    本模块中提供了TextNode 和 VariableNode

        2.3.1 TextNode 文本节点对象
        作用：用于保存纯文本的内容，其渲染函数只返回自身保存的字符串
        属性：
        1. s. 保存文本内容
        方法：
        __init__(s), 传入节点的文本值s
        render()重载，直接输出s的内容

        2.3.2 VariableNode 变量节点对象
        作用：对变量(包含过滤器) 进行渲染，调用 FilterExpression的resolve()进行渲染，然后对结果进行转义处理
        属性：
        1. filter_expression. 传入的过滤器表达式实例
        方法：
        1. __init__(expression)，传入一个过滤器表达式
        2. render()重载，调用(filter_expression.render() --> Variable.render() --> 过滤器处理) --> 类型转换并转义

    2.4 NodeList 节点列表对象
    作用：保存节点的列表对象
    属性：
    1. contains_nontext. 是否包含非TextNode
    方法：
    1. get_nodes_by_type(nodetype). 类似于Node中的同名函数，遍历所有节点并调用所有节点的同名函数
    2. render(context). 渲染当前列表中的所有节点

3. 模板包装器 Template
作用：封装模板的编译和渲染过程，方便使用者使用
一般情况下，不直接使用Template的实例化，而是使用Engine
核心：compile_nodelist()编译出节点；render()渲染节点
属性：
1. name. 模板名称
2. source
3. origin. 模板文件名
4. nodelist. 调用compile_nodelist解析出的NodeList()实例
5. engine. 模板处理引擎
方法：
1. compile_nodelist. 编译输出节点，返回NodeList()
2. render(). 渲染模板



How it works:

The Lexer.tokenize() method converts a template string (i.e., a string
containing markup with custom template tags) to tokens, which can be either
plain text (TokenType.TEXT), variables (TokenType.VAR), or block statements
(TokenType.BLOCK).

The Parser() class takes a list of tokens in its constructor, and its parse()
method returns a compiled template -- which is, under the hood, a list of
Node objects.

Each Node is responsible for creating some sort of output -- e.g. simple text
(TextNode), variable values in a given context (VariableNode), results of basic
logic (IfNode), results of looping (ForNode), or anything else. The core Node
types are TextNode, VariableNode, IfNode and ForNode, but plugin modules can
define their own custom node types.

Each Node has a render() method, which takes a Context and returns a string of
the rendered node. For example, the render() method of a Variable Node returns
the variable's value as a string. The render() method of a ForNode returns the
rendered output of whatever was inside the loop, recursively.

The Template class is a convenient wrapper that takes care of template
compilation and rendering.

Usage:

The only thing you should ever use directly in this file is the Template class.
Create a compiled template object with a template_string, then call render()
with a context. In the compilation stage, the TemplateSyntaxError exception
will be raised if the template doesn't have proper syntax.

Sample code:

>>> from django import template
>>> s = '<html>{% if test %}<h1>{{ varvalue }}</h1>{% endif %}</html>'
>>> t = template.Template(s)

(t is now a compiled template, and its render() method can be called multiple
times with multiple contexts)

>>> c = template.Context({'test':True, 'varvalue': 'Hello'})
>>> t.render(c)
'<html><h1>Hello</h1></html>'
>>> c = template.Context({'test':False, 'varvalue': 'Hello'})
>>> t.render(c)
'<html></html>'
"""

import logging
import re
from enum import Enum
from inspect import getcallargs, getfullargspec, unwrap

from django.template.context import (  # NOQA: imported for backwards compatibility
    BaseContext, Context, ContextPopException, RequestContext,
)
from django.utils.formats import localize
from django.utils.html import conditional_escape, escape
from django.utils.safestring import SafeData, mark_safe
from django.utils.text import (
    get_text_list, smart_split, unescape_string_literal,
)
from django.utils.timezone import template_localtime
from django.utils.translation import gettext_lazy, pgettext_lazy

from .exceptions import TemplateSyntaxError

# template syntax constants
FILTER_SEPARATOR = '|'
FILTER_ARGUMENT_SEPARATOR = ':'
VARIABLE_ATTRIBUTE_SEPARATOR = '.'
BLOCK_TAG_START = '{%'
BLOCK_TAG_END = '%}'
VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'
COMMENT_TAG_START = '{#'
COMMENT_TAG_END = '#}'
TRANSLATOR_COMMENT_MARK = 'Translators'
SINGLE_BRACE_START = '{'
SINGLE_BRACE_END = '}'

# what to report as the origin for templates that come from non-loader sources
# (e.g. strings)
UNKNOWN_SOURCE = '<unknown source>'

# match a variable or block tag and capture the entire tag, including start/end
# delimiters
tag_re = (re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' %
          (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
           re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END),
           re.escape(COMMENT_TAG_START), re.escape(COMMENT_TAG_END))))

logger = logging.getLogger('django.template')


class TokenType(Enum):
    TEXT = 0
    VAR = 1
    BLOCK = 2
    COMMENT = 3


class VariableDoesNotExist(Exception):

    def __init__(self, msg, params=()):
        self.msg = msg
        self.params = params

    def __str__(self):
        return self.msg % self.params


class Origin:
    """
    保存模板源文件名以及加载器对象
    """
    def __init__(self, name, template_name=None, loader=None):
        self.name = name
        self.template_name = template_name
        self.loader = loader

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return (
            isinstance(other, Origin) and
            self.name == other.name and
            self.loader == other.loader
        )

    @property
    def loader_name(self):
        if self.loader:
            return '%s.%s' % (
                self.loader.__module__, self.loader.__class__.__name__,
            )


class Template:
    """
    建议直接使用Engine来实例化Template
    这个类保留向后兼容直接创建和实例化模板的能力
    """
    def __init__(self, template_string, origin=None, name=None, engine=None):
        """
        实例化模板对象
        根据传入的模板字符串、engine，对模板字符串进行解析和编译
        输出编译后的Node对象
        :param template_string: 模板字符串，例如 {{ user_name }}
        :param origin: 模板文件
        :param name:
        :param engine:
        """
        # If Template is instantiated directly rather than from an Engine and
        # exactly one Django template engine is configured, use that engine.
        # This is required to preserve backwards-compatibility for direct use
        # e.g. Template('...').render(Context({...}))
        if engine is None:
            from .engine import Engine
            engine = Engine.get_default()
        if origin is None:
            origin = Origin(UNKNOWN_SOURCE)
        self.name = name
        self.origin = origin
        self.engine = engine
        self.source = str(template_string)  # May be lazy.
        self.nodelist = self.compile_nodelist()

    def __iter__(self):
        for node in self.nodelist:
            yield from node

    def _render(self, context):
        return self.nodelist.render(context)

    def render(self, context):
        "Display stage -- can be called many times"
        with context.render_context.push_state(self):
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    return self._render(context)
            else:
                return self._render(context)

    def compile_nodelist(self):
        """
        Parse and compile the template source into a nodelist. If debug
        is True and an exception occurs during parsing, the exception is
        is annotated with contextual line information where it occurred in the
        template source.
        """
        if self.engine.debug:
            lexer = DebugLexer(self.source)
        else:
            lexer = Lexer(self.source)

        tokens = lexer.tokenize()
        parser = Parser(
            tokens, self.engine.template_libraries, self.engine.template_builtins,
            self.origin,
        )

        try:
            return parser.parse()
        except Exception as e:
            if self.engine.debug:
                e.template_debug = self.get_exception_info(e, e.token)
            raise

    def get_exception_info(self, exception, token):
        """
        Return a dictionary containing contextual line information of where
        the exception occurred in the template. The following information is
        provided:

        message
            The message of the exception raised.

        source_lines
            The lines before, after, and including the line the exception
            occurred on.

        line
            The line number the exception occurred on.

        before, during, after
            The line the exception occurred on split into three parts:
            1. The content before the token that raised the error.
            2. The token that raised the error.
            3. The content after the token that raised the error.

        total
            The number of lines in source_lines.

        top
            The line number where source_lines starts.

        bottom
            The line number where source_lines ends.

        start
            The start position of the token in the template source.

        end
            The end position of the token in the template source.
        """
        start, end = token.position
        context_lines = 10
        line = 0
        upto = 0
        source_lines = []
        before = during = after = ""
        for num, next in enumerate(linebreak_iter(self.source)):
            if start >= upto and end <= next:
                line = num
                before = escape(self.source[upto:start])
                during = escape(self.source[start:end])
                after = escape(self.source[end:next])
            source_lines.append((num, escape(self.source[upto:next])))
            upto = next
        total = len(source_lines)

        top = max(1, line - context_lines)
        bottom = min(total, line + 1 + context_lines)

        # In some rare cases exc_value.args can be empty or an invalid
        # string.
        try:
            message = str(exception.args[0])
        except (IndexError, UnicodeDecodeError):
            message = '(Could not get exception message)'

        return {
            'message': message,
            'source_lines': source_lines[top:bottom],
            'before': before,
            'during': during,
            'after': after,
            'top': top,
            'bottom': bottom,
            'total': total,
            'line': line,
            'name': self.origin.name,
            'start': start,
            'end': end,
        }


def linebreak_iter(template_source):
    yield 0
    p = template_source.find('\n')
    while p >= 0:
        yield p + 1
        p = template_source.find('\n', p + 1)
    yield len(template_source) + 1


class Token:
    """
    从模板中分隔出的词法标记，使用Token对象存储
    属性：
    1. token_type. 标记的类型，.TEXT, .VAR, .BLOCK, or .COMMENT
    2. contents. 标记的原始字符串，去掉了两边的空格
    3. position. 在模板中的位置(字符位置)，是一个tuple类型 (start, stop)
    4. lineno. 在模板中的行号，通过判断'\n'的数量确定
    方法：
    1. split_contents(self)
    作用：分隔self.contents中的内容，使用' '分隔
    返回：字符串列表list
    """
    def __init__(self, token_type, contents, position=None, lineno=None):
        """
        A token representing a string from the template.

        token_type
            A TokenType, either .TEXT, .VAR, .BLOCK, or .COMMENT.

        contents
            The token source string.

        position
            An optional tuple containing the start and end index of the token
            in the template source. This is used for traceback information
            when debug is on.

        lineno
            The line number the token appears on in the template source.
            This is used for traceback information and gettext files.
        """
        self.token_type, self.contents = token_type, contents
        self.lineno = lineno
        self.position = position

    def __str__(self):
        token_name = self.token_type.name.capitalize()
        return ('<%s token: "%s...">' %
                (token_name, self.contents[:20].replace('\n', '')))

    def split_contents(self):
        """
        分隔contents中的内容，使用' '分隔
        1. smart_split，不分割'"包含的内容
        2. 如果使用翻译，则正确处理。例如： '_("a" "b" "c")' ==> '_("a" "b" "c")'，不会拆分成三个部分
        :return: 字符串list
        """
        split = []
        bits = smart_split(self.contents)
        for bit in bits:
            # Handle translation-marked template pieces
            if bit.startswith(('_("', "_('")):
                sentinel = bit[2] + ')'
                trans_bit = [bit]
                while not bit.endswith(sentinel):
                    bit = next(bits)
                    trans_bit.append(bit)
                bit = ' '.join(trans_bit)
            split.append(bit)
        return split


class Lexer:
    def __init__(self, template_string):
        self.template_string = template_string
        self.verbatim = False

    def tokenize(self):
        """
        Return a list of tokens from a given template_string.
        """
        in_tag = False
        lineno = 1
        result = []
        for bit in tag_re.split(self.template_string):
            if bit:
                result.append(self.create_token(bit, None, lineno, in_tag))
            in_tag = not in_tag
            lineno += bit.count('\n')
        return result

    def create_token(self, token_string, position, lineno, in_tag):
        """
        Convert the given token string into a new Token object and return it.
        If in_tag is True, we are processing something that matched a tag,
        otherwise it should be treated as a literal string.
        """
        if in_tag and token_string.startswith(BLOCK_TAG_START):
            # The [2:-2] ranges below strip off *_TAG_START and *_TAG_END.
            # We could do len(BLOCK_TAG_START) to be more "correct", but we've
            # hard-coded the 2s here for performance. And it's not like
            # the TAG_START values are going to change anytime, anyway.
            block_content = token_string[2:-2].strip()
            if self.verbatim and block_content == self.verbatim:
                self.verbatim = False
        if in_tag and not self.verbatim:
            if token_string.startswith(VARIABLE_TAG_START):
                return Token(TokenType.VAR, token_string[2:-2].strip(), position, lineno)
            elif token_string.startswith(BLOCK_TAG_START):
                if block_content[:9] in ('verbatim', 'verbatim '):
                    self.verbatim = 'end%s' % block_content
                return Token(TokenType.BLOCK, block_content, position, lineno)
            elif token_string.startswith(COMMENT_TAG_START):
                content = ''
                if token_string.find(TRANSLATOR_COMMENT_MARK):
                    content = token_string[2:-2].strip()
                return Token(TokenType.COMMENT, content, position, lineno)
        else:
            return Token(TokenType.TEXT, token_string, position, lineno)


class DebugLexer(Lexer):
    def tokenize(self):
        """
        Split a template string into tokens and annotates each token with its
        start and end position in the source. This is slower than the default
        lexer so only use it when debug is True.
        """
        lineno = 1
        result = []
        upto = 0
        for match in tag_re.finditer(self.template_string):
            start, end = match.span()
            if start > upto:
                token_string = self.template_string[upto:start]
                result.append(self.create_token(token_string, (upto, start), lineno, in_tag=False))
                lineno += token_string.count('\n')
                upto = start
            token_string = self.template_string[start:end]
            result.append(self.create_token(token_string, (start, end), lineno, in_tag=True))
            lineno += token_string.count('\n')
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
            result.append(self.create_token(last_bit, (upto, upto + len(last_bit)), lineno, in_tag=False))
        return result


class Parser:
    def __init__(self, tokens, libraries=None, builtins=None, origin=None):
        # 保存原始 Token 列表
        self.tokens = tokens
        # 注册的Tag
        self.tags = {}
        # 注册的过滤器
        self.filters = {}
        # Block Token的处理堆栈，用于调试使用
        self.command_stack = []
        # 自定义的包含tag和filter模块
        if libraries is None:
            libraries = {}
        # django内置的tag和filter模块
        if builtins is None:
            builtins = []
        # 如果没有传入一下三个参数，则该parser无法处理Block类型的Token
        self.libraries = libraries
        for builtin in builtins:
            self.add_library(builtin)
        # 模板文件的全路径名称
        self.origin = origin

    def parse(self, parse_until=None):
        """
        parse_until 传入的值是一个tuple，例如('endblock',)
        当接token是BLOCK类型，且包含block命令时，会执行do_block()标签处理函数，在处理函数中，继续调用parse()方法，并传入parse_until=('endblock',)
        表示用parse()方法递归处理self.tokens，当遇到block时，直到遇到parse_until中包含的命令时，返回nodelist
        返回的nodelist会包含在BLOCKNODE节点对象中

        通过递归调用的方式，逐级分解并处理
        {% block a %}
            {% url 'index.html' %}
            {{ user_name }}
        {% endblock a %}
        以上token最终生成一个BLOCKNODE实例，该实例的nodelist属性包含一个URLNODE和VariantNODE实例

        可以这样理解：parse()函数执行完会返回一个 Node 列表，该列表中的某个 Node 也包含一个列表
        这种关系是因为在模板中块Token{% %}的存在，在块Token中，允许包含Text Var 和 Block
        这是一个嵌套的节点关系，所以必须用递归的方式进行处理

        Iterate through the parser tokens and compiles each one into a node.

        If parse_until is provided, parsing will stop once one of the
        specified tokens has been reached. This is formatted as a list of
        tokens, e.g. ['elif', 'else', 'endif']. If no matching token is
        reached, raise an exception with the unclosed block tag details.
        """
        # 如果没有本次迭代终止的标志，则置空
        if parse_until is None:
            parse_until = []
        # 初始化本次迭代需要输出的 Node list
        nodelist = NodeList()
        # 自顶向下遍历所有Token
        while self.tokens:
            # 依次取出第一个Token
            token = self.next_token()
            # Use the raw values here for TokenType.* for a tiny performance boost.
            # 如果是纯文本类型的Token
            if token.token_type.value == 0:  # TokenType.TEXT
                # 创建一个TextNode实例，并将其添加到 nodelist 变量中
                self.extend_nodelist(nodelist, TextNode(token.contents), token)
            elif token.token_type.value == 1:  # TokenType.VAR
                # 变量Token {{ }}
                if not token.contents:
                    raise self.error(token, 'Empty variable tag on line %d' % token.lineno)
                try:
                    # 处理变量，生成过滤器表达式对象，该对象是创建 VariableNode 的参数
                    # filter_expression 分离变量中的过滤器以及过滤器参数
                    # filter_expression 在渲染时，使用注册的过滤器方法对变量的值进行处理
                    filter_expression = self.compile_filter(token.contents)
                except TemplateSyntaxError as e:
                    raise self.error(token, e)
                # 创建一个 VariableNode ，该Node对象包含一个FilterExpression对象
                var_node = VariableNode(filter_expression)
                self.extend_nodelist(nodelist, var_node, token)
            elif token.token_type.value == 2:  # TokenType.BLOCK
                try:
                    # 取出 Block 中第一个分隔的字符串，这个是块的命令，如：block url static if for ...
                    command = token.contents.split()[0]
                except IndexError:
                    raise self.error(token, 'Empty block tag on line %d' % token.lineno)
                # 如果当前块命令是本次迭代的结束
                # 例如：block 块 结束 endblock
                if command in parse_until:
                    # A matching token has been reached. Return control to
                    # the caller. Put the token back on the token list so the
                    # caller knows where it terminated.
                    # 在Token队列的头部插入当前的结束Token，因为调用方会利用这个Token判断是否结束，例如：elif else 等
                    self.prepend_token(token)
                    # 将块内的节点返回给调用方，作为 Node 中的子Node
                    return nodelist
                # Add the token to the command stack. This is used for error
                # messages if further parsing fails due to an unclosed block
                # tag.
                # 主要用于调试使用，当Block中的命令处理函数执行过程中发生异常，就可以查看具体哪个块出现了问题
                self.command_stack.append((command, token))
                # Get the tag callback function from the ones registered with
                # the parser.
                try:
                    # 根据块的命令，取出已经注册的 Tag
                    compile_func = self.tags[command]
                except KeyError:
                    self.invalid_block_tag(token, command, parse_until)
                # Compile the callback into a node object and add it to
                # the node list.
                try:
                    # 执行已注册的 Tag 的处理函数，注意传入的参数为：parser 和 token
                    compiled_result = compile_func(self, token)
                except Exception as e:
                    raise self.error(token, e)
                # Tag处理函数一定要返回一个 Node 的实例
                # 将该 Node 添加到当前迭代的 nodelist 中
                self.extend_nodelist(nodelist, compiled_result, token)
                # Compile success. Remove the token from the command stack.
                # 处理成功，就把当前块移出堆栈
                self.command_stack.pop()
        # 当所有的Token都处理完
        # 这是parse_until不为空，表示有Block还没有结束，即没有结束的块，表示语法错误
        if parse_until:
            self.unclosed_block_tag(parse_until)
        # 将解析完成的 Node 列表返回
        return nodelist

    def skip_past(self, endtag):
        while self.tokens:
            token = self.next_token()
            if token.token_type == TokenType.BLOCK and token.contents == endtag:
                return
        self.unclosed_block_tag([endtag])

    def extend_nodelist(self, nodelist, node, token):
        # Check that non-text nodes don't appear before an extends tag.
        if node.must_be_first and nodelist.contains_nontext:
            raise self.error(
                token, '%r must be the first tag in the template.' % node,
            )
        # 判断nodelist 节点列表中，是否包含非 TextNode
        if isinstance(nodelist, NodeList) and not isinstance(node, TextNode):
            nodelist.contains_nontext = True
        # Set origin and token here since we can't modify the node __init__()
        # method.
        # Node 没有构造函数保存token和origin，所以，必须手动设置这两个属性
        node.token = token
        node.origin = self.origin
        nodelist.append(node)

    def error(self, token, e):
        """
        Return an exception annotated with the originating token. Since the
        parser can be called recursively, check if a token is already set. This
        ensures the innermost token is highlighted if an exception occurs,
        e.g. a compile error within the body of an if statement.
        """
        if not isinstance(e, Exception):
            e = TemplateSyntaxError(e)
        if not hasattr(e, 'token'):
            e.token = token
        return e

    def invalid_block_tag(self, token, command, parse_until=None):
        if parse_until:
            raise self.error(
                token,
                "Invalid block tag on line %d: '%s', expected %s. Did you "
                "forget to register or load this tag?" % (
                    token.lineno,
                    command,
                    get_text_list(["'%s'" % p for p in parse_until], 'or'),
                ),
            )
        raise self.error(
            token,
            "Invalid block tag on line %d: '%s'. Did you forget to register "
            "or load this tag?" % (token.lineno, command)
        )

    def unclosed_block_tag(self, parse_until):
        command, token = self.command_stack.pop()
        msg = "Unclosed tag on line %d: '%s'. Looking for one of: %s." % (
            token.lineno,
            command,
            ', '.join(parse_until),
        )
        raise self.error(token, msg)

    def next_token(self):
        return self.tokens.pop(0)

    def prepend_token(self, token):
        self.tokens.insert(0, token)

    def delete_first_token(self):
        del self.tokens[0]

    def add_library(self, lib):
        self.tags.update(lib.tags)
        self.filters.update(lib.filters)

    def compile_filter(self, token):
        """
        Convenient wrapper for FilterExpression
        """
        return FilterExpression(token, self)

    def find_filter(self, filter_name):
        if filter_name in self.filters:
            return self.filters[filter_name]
        else:
            raise TemplateSyntaxError("Invalid filter: '%s'" % filter_name)


# This only matches constant *strings* (things in quotes or marked for
# translation). Numbers are treated as variables for implementation reasons
# (so that they retain their type when passed to filters).
constant_string = r"""
(?:%(i18n_open)s%(strdq)s%(i18n_close)s|
%(i18n_open)s%(strsq)s%(i18n_close)s|
%(strdq)s|
%(strsq)s)
""" % {
    'strdq': r'"[^"\\]*(?:\\.[^"\\]*)*"',  # double-quoted string
    'strsq': r"'[^'\\]*(?:\\.[^'\\]*)*'",  # single-quoted string
    'i18n_open': re.escape("_("),
    'i18n_close': re.escape(")"),
}
constant_string = constant_string.replace("\n", "")

filter_raw_string = r"""
^(?P<constant>%(constant)s)|
^(?P<var>[%(var_chars)s]+|%(num)s)|
 (?:\s*%(filter_sep)s\s*
     (?P<filter_name>\w+)
         (?:%(arg_sep)s
             (?:
              (?P<constant_arg>%(constant)s)|
              (?P<var_arg>[%(var_chars)s]+|%(num)s)
             )
         )?
 )""" % {
    'constant': constant_string,
    'num': r'[-+\.]?\d[\d\.e]*',
    'var_chars': r'\w\.',
    'filter_sep': re.escape(FILTER_SEPARATOR),
    'arg_sep': re.escape(FILTER_ARGUMENT_SEPARATOR),
}

filter_re = re.compile(filter_raw_string, re.VERBOSE)


class FilterExpression:
    """
    解析变量标识的内容
    分离出：常量(' ' " ")和变量
    分离出：过滤器名称，过滤器参数
    属性：
    1. var 变量对象 Variable
    2. filters 保存过滤器的列表 [(func, [(False, Variable), (True, Variable)]), ]

    Parse a variable token and its optional filters (all as a single string),
    and return a list of tuples of the filter name and arguments.
    Sample::

        >>> token = 'variable|default:"Default value"|date:"Y-m-d"'
        >>> p = Parser('')
        >>> fe = FilterExpression(token, p)
        >>> len(fe.filters)
        2
        >>> fe.var
        <Variable: 'variable'>
    """
    def __init__(self, token, parser):
        """
        构造函数
        :param token: 变量标识，是字符串,Token对象的内容
        :param parser: Parser实例
        """
        self.token = token
        # 使用正则表达式分隔变量、过滤器、过滤器参数
        matches = filter_re.finditer(token)
        # 变量
        var_obj = None
        # 过滤器列表
        # [(func, [(False, Variable), (True, Variable)]), ]
        filters = []
        upto = 0
        for match in matches:
            start = match.start()
            if upto != start:
                raise TemplateSyntaxError("Could not parse some characters: "
                                          "%s|%s|%s" %
                                          (token[:upto], token[upto:start],
                                           token[start:]))
            # 如果变量没有赋值，则说明当前处理的是变量
            if var_obj is None:
                # 取出解析出的变量名和常量名
                var, constant = match.group("var", "constant")
                if constant:
                    try:
                        # 如果是常量，直接创建 Variable 对象
                        # 因为有可能，constant 是需要翻译的，因此，需要调用 resolve()进行处理
                        var_obj = Variable(constant).resolve({})
                    except VariableDoesNotExist:
                        var_obj = None
                elif var is None:
                    raise TemplateSyntaxError("Could not find variable at "
                                              "start of %s." % token)
                else:
                    # 创建变量对象，变量的渲染需要context，因此这里只是创建
                    var_obj = Variable(var)
            else:
                # 如果已经处理了变量，则后面的都是过滤器
                # 取出过滤器的名称
                filter_name = match.group("filter_name")
                args = []
                # 取出过滤器的参数名
                constant_arg, var_arg = match.group("constant_arg", "var_arg")
                if constant_arg:
                    args.append((False, Variable(constant_arg).resolve({})))
                elif var_arg:
                    args.append((True, Variable(var_arg)))
                # 从parser中查找过滤器对应的处理函数
                filter_func = parser.find_filter(filter_name)
                # 检查过滤器函数是否有效
                self.args_check(filter_name, filter_func, args)
                filters.append((filter_func, args))
            upto = match.end()
        if upto != len(token):
            raise TemplateSyntaxError("Could not parse the remainder: '%s' "
                                      "from '%s'" % (token[upto:], token))

        self.filters = filters
        self.var = var_obj

    def resolve(self, context, ignore_failures=False):
        """
        基于 context 上下文，生成处理后的结果
        :param context: 上下文 Context对象
        :param ignore_failures: 是否忽略异常
        :return:
        """
        # 如果 var 是一个 Variable
        # 有可能是一个 None
        if isinstance(self.var, Variable):
            try:
                # 调用 Variable 的处理函数，得到处理后的结果
                obj = self.var.resolve(context)
            except VariableDoesNotExist:
                if ignore_failures:
                    obj = None
                else:
                    string_if_invalid = context.template.engine.string_if_invalid
                    if string_if_invalid:
                        if '%s' in string_if_invalid:
                            return string_if_invalid % self.var
                        else:
                            return string_if_invalid
                    else:
                        obj = string_if_invalid
        else:
            obj = self.var

        # 对变量的值进行过滤器处理
        for func, args in self.filters:
            arg_vals = []
            for lookup, arg in args:
                # args是一个tuple (False, Variable)
                if not lookup:
                    arg_vals.append(mark_safe(arg))
                else:
                    # 过滤器变参，需要先对变参进行处理
                    arg_vals.append(arg.resolve(context))
            # 还不清楚下面代码的含义
            # 用 @register.filter 注册过滤器处理函数时，传入的 flags
            # 固定可选项为: ('expects_localtime', 'is_safe', 'needs_autoescape') 之一
            # 将传入的参数设置为 func 的属性
            if getattr(func, 'expects_localtime', False):
                obj = template_localtime(obj, context.use_tz)
            if getattr(func, 'needs_autoescape', False):
                new_obj = func(obj, autoescape=context.autoescape, *arg_vals)
            else:
                # 执行过滤器处理函数，返回处理结果
                new_obj = func(obj, *arg_vals)
            if getattr(func, 'is_safe', False) and isinstance(obj, SafeData):
                obj = mark_safe(new_obj)
            else:
                obj = new_obj
        return obj

    def args_check(name, func, provided):
        provided = list(provided)
        # First argument, filter input, is implied.
        plen = len(provided) + 1
        # Check to see if a decorator is providing the real function.
        func = unwrap(func)

        args, _, _, defaults, _, _, _ = getfullargspec(func)
        alen = len(args)
        dlen = len(defaults or [])
        # Not enough OR Too many
        if plen < (alen - dlen) or plen > alen:
            raise TemplateSyntaxError("%s requires %d arguments, %d provided" %
                                      (name, alen - dlen, plen))

        return True
    args_check = staticmethod(args_check)

    def __str__(self):
        return self.token


class Variable:
    """
    1. 解析模板中的变量
    2. 根据传入环境变量context，解析出变量的值
    3. 支持字符串、变量、对象
    A template variable, resolvable against a given context. The variable may
    be a hard-coded string (if it begins and ends with single or double quote
    marks)::

        >>> c = {'article': {'section':'News'}}
        >>> Variable('article.section').resolve(c)
        'News'
        >>> Variable('article').resolve(c)
        {'section': 'News'}
        >>> class AClass: pass
        >>> c = AClass()
        >>> c.article = AClass()
        >>> c.article.section = 'News'

    (The example assumes VARIABLE_ATTRIBUTE_SEPARATOR is '.')
    """

    def __init__(self, var):
        """
        :param var: 变量模板字符串，注意：必须是字符串类型
        执行过程：
        1. 先判断传入的字符串是否是数值类型
            1.1 如果包含'.'、'e'字符，有可能是浮点类型，float()
                1.1.2 字符串以'.'结尾，不是有效的数值，例如：2.
            1.2 否则可能是整形 int()
            1.3 如果异常则进入2
        2. 是需要翻译的内容，以'_('开头，')'结尾
            2.1 设置变量对象的translate属性为True
        3. 如果以'"包围，例如："123"或者'123'，则转换为字符串，去掉'"符号
        4. 拆分为变量、对象
        处理结果：
        1. 如果是数值类型或者字符串，放到literal属性中
        1.1 如果是需要翻译的字符串，设置translate = True
        2. 如果是变量类型，以'.'分解后，放到lookups中，是一个tuple
        """
        # 保存传入的模板字符串
        self.var = var
        # 模板解析结果（文本、数值），保存
        self.literal = None
        # 模板解析结果（对象、变量），保存
        self.lookups = None
        # 模板解析结果为需要翻译的文本，保存为True
        self.translate = False
        # 模板中包含%，可以使用message_content，组合后输出
        self.message_context = None

        # 传入的var变量必须是一个字符串类型
        if not isinstance(var, str):
            raise TypeError(
                "Variable must be a string or number, got %s" % type(var))
        try:
            # First try to treat this variable as a number.
            #
            # Note that this could cause an OverflowError here that we're not
            # catching. Since this should only happen at compile time, that's
            # probably OK.

            # Try to interpret values containing a period or an 'e'/'E'
            # (possibly scientific notation) as a float;  otherwise, try int.
            # 先判断是否数值类型
            # 如果包含'.'或'e'，有可能是浮点数
            if '.' in var or 'e' in var.lower():
                self.literal = float(var)
                # "2." is invalid
                # 结尾不能是'.'
                if var.endswith('.'):
                    raise ValueError
            else:
                # 不是浮点，有可能是整形
                self.literal = int(var)
        except ValueError:
            # 如果不是数值类型，转换触发异常
            # A ValueError means that the variable isn't a number.
            # 如果是一个需要翻译的数据
            if var.startswith('_(') and var.endswith(')'):
                # The result of the lookup should be translated at rendering
                # time.
                # 设置需要翻译标志，在渲染时再处理
                self.translate = True
                # 去掉翻译的前后标志'_('和')'
                var = var[2:-1]
            # If it's wrapped with quotes (single or double), then
            # we're also dealing with a literal.
            try:
                # unescape_string_literal() 去掉字符串头尾的'或"，并对字符串中的\"和\\进行反向转义
                # 如果没有'"，则触发ValueError异常，也就是说该数据应该是一个变量或对象
                # make_safe() 将字符串转换为SafeText对象实例
                self.literal = mark_safe(unescape_string_literal(var))
            except ValueError:
                # Otherwise we'll set self.lookups so that resolve() knows we're
                # dealing with a bonafide variable
                # 只能是变量或者对象了
                # 变量或对象的属性，都不可以'_'开头
                if var.find(VARIABLE_ATTRIBUTE_SEPARATOR + '_') > -1 or var[0] == '_':
                    raise TemplateSyntaxError("Variables and attributes may "
                                              "not begin with underscores: '%s'" %
                                              var)
                # 将变量以'.'拆分为多个变量，保存到lookups中
                self.lookups = tuple(var.split(VARIABLE_ATTRIBUTE_SEPARATOR))

    def resolve(self, context):
        """
        Resolve this variable against a given context.
        基于传入的context字典，处理变量的值，也就是说，如果是变量/对象，则通过该方法，可以得到变量的值
        :return 处理结果
        """
        if self.lookups is not None:
            # We're dealing with a variable that needs to be resolved
            value = self._resolve_lookup(context)
        else:
            # 如果不是变量，而是字符串或数值，不需要进行处理，直接返回其值
            # We're dealing with a literal, so it's already been "resolved"
            value = self.literal
        # 如果需要翻译
        if self.translate:
            is_safe = isinstance(value, SafeData)
            msgid = value.replace('%', '%%')
            msgid = mark_safe(msgid) if is_safe else msgid
            # 没有看明白pgettext_lazy的执行过程
            # 使用decorator封装，返回一个promise对象
            if self.message_context:
                return pgettext_lazy(self.message_context, msgid)
            else:
                return gettext_lazy(msgid)
        return value

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.var)

    def __str__(self):
        return self.var

    def _resolve_lookup(self, context):
        """
        处理变量/对象的内部方法
        Perform resolution of a real variable (i.e. not a literal) against the
        given context.

        As indicated by the method's name, this method is an implementation
        detail and shouldn't be called by external code. Use Variable.resolve()
        instead.
        """
        current = context
        try:  # catch-all for silent variable failures
            # 依次取出变量的名称
            # 如：opts.app_label ==> ('opts', 'app_label')
            # 先取出opts，再取出app_label
            for bit in self.lookups:
                try:  # dictionary lookup
                    # context是Context实例
                    # 先使用字典方式取数据
                    # 取出来后，就更新current值
                    current = current[bit]
                    # ValueError/IndexError are for numpy.array lookup on
                    # numpy < 1.9 and 1.9+ respectively
                except (TypeError, AttributeError, KeyError, ValueError, IndexError):
                    try:  # attribute lookup
                        # Don't return class attributes if the class is the context:
                        if isinstance(current, BaseContext) and getattr(type(current), bit):
                            raise AttributeError
                        # 如果字典方式访问无效
                        # 尝试使用属性方式访问
                        current = getattr(current, bit)
                    except (TypeError, AttributeError):
                        # Reraise if the exception was raised by a @property
                        if not isinstance(current, BaseContext) and bit in dir(current):
                            raise
                        try:  # list-index lookup
                            current = current[int(bit)]
                        except (IndexError,  # list index out of range
                                ValueError,  # invalid literal for int()
                                KeyError,    # current is a dict without `int(bit)` key
                                TypeError):  # unsubscriptable object
                            raise VariableDoesNotExist("Failed lookup for key "
                                                       "[%s] in %r",
                                                       (bit, current))  # missing attribute
                # 如果变量是可调用的
                if callable(current):
                    if getattr(current, 'do_not_call_in_templates', False):
                        pass
                    elif getattr(current, 'alters_data', False):
                        current = context.template.engine.string_if_invalid
                    else:
                        try:  # method call (assuming no args required)
                            # 调用对象并返回结果，必须是无入参的方法
                            current = current()
                        except TypeError:
                            try:
                                getcallargs(current)
                            except TypeError:  # arguments *were* required
                                current = context.template.engine.string_if_invalid  # invalid method call
                            else:
                                raise
        except Exception as e:
            template_name = getattr(context, 'template_name', None) or 'unknown'
            logger.debug(
                "Exception while resolving variable '%s' in template '%s'.",
                bit,
                template_name,
                exc_info=True,
            )

            if getattr(e, 'silent_variable_failure', False):
                current = context.template.engine.string_if_invalid
            else:
                raise

        return current


class Node:
    # Set this to True for nodes that must be first in the template (although
    # they can be preceded by text nodes.
    must_be_first = False
    child_nodelists = ('nodelist',)
    token = None

    def render(self, context):
        """
        Return the node rendered as a string.
        """
        pass

    def render_annotated(self, context):
        """
        Render the node. If debug is True and an exception occurs during
        rendering, the exception is annotated with contextual line information
        where it occurred in the template. For internal usage this method is
        preferred over using the render method directly.
        """
        try:
            return self.render(context)
        except Exception as e:
            if context.template.engine.debug and not hasattr(e, 'template_debug'):
                e.template_debug = context.render_context.template.get_exception_info(e, self.token)
            raise

    def __iter__(self):
        yield self

    def get_nodes_by_type(self, nodetype):
        """
        Return a list of all nodes (within this node and its nodelist)
        of the given type
        """
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        for attr in self.child_nodelists:
            nodelist = getattr(self, attr, None)
            if nodelist:
                nodes.extend(nodelist.get_nodes_by_type(nodetype))
        return nodes


class NodeList(list):
    # Set to True the first time a non-TextNode is inserted by
    # extend_nodelist().
    contains_nontext = False

    def render(self, context):
        bits = []
        for node in self:
            if isinstance(node, Node):
                bit = node.render_annotated(context)
            else:
                bit = node
            bits.append(str(bit))
        return mark_safe(''.join(bits))

    def get_nodes_by_type(self, nodetype):
        "Return a list of all nodes of the given type"
        nodes = []
        for node in self:
            nodes.extend(node.get_nodes_by_type(nodetype))
        return nodes


class TextNode(Node):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.s[:25])

    def render(self, context):
        return self.s


def render_value_in_context(value, context):
    """
    Convert any value to a string to become part of a rendered template. This
    means escaping, if required, and conversion to a string. If value is a
    string, it's expected to already be translated.
    """
    # 转换datetime类型的value --> string值
    value = template_localtime(value, use_tz=context.use_tz)
    # 本地化输出
    value = localize(value, use_l10n=context.use_l10n)
    if context.autoescape:
        if not issubclass(type(value), str):
            value = str(value)
        # 自动转义
        return conditional_escape(value)
    else:
        return str(value)


class VariableNode(Node):
    def __init__(self, filter_expression):
        self.filter_expression = filter_expression

    def __repr__(self):
        return "<Variable Node: %s>" % self.filter_expression

    def render(self, context):
        try:
            output = self.filter_expression.resolve(context)
        except UnicodeDecodeError:
            # Unicode conversion can fail sometimes for reasons out of our
            # control (e.g. exception rendering). In that case, we fail
            # quietly.
            return ''
        return render_value_in_context(output, context)


# Regex for token keyword arguments
kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")


def token_kwargs(bits, parser, support_legacy=False):
    """
    解析 Token 中 的关键字参数 并 返回 {param_name: FilterExpression(param_Value)}
    如果不是关键字参数，则返回 {}

    :param bits list(str) Token 中的关键字参数
    :param support_legacy boolean True--支持 as 语句; False--必须是 = 语句

    示例如下：
    {% include xxxx with name=opts.verbose_name %}

    返回 {'name': FilterExpression('opts.verbose_name', parser)}

    Parse token keyword arguments and return a dictionary of the arguments
    retrieved from the ``bits`` token list.

    `bits` is a list containing the remainder of the token (split by spaces)
    that is to be checked for arguments. Valid arguments are removed from this
    list.

    `support_legacy` - if True, the legacy format ``1 as foo`` is accepted.
    Otherwise, only the standard ``foo=1`` format is allowed.

    There is no requirement for all remaining token ``bits`` to be keyword
    arguments, so return the dictionary as soon as an invalid argument format
    is reached.
    """
    if not bits:
        return {}
    match = kwarg_re.match(bits[0])
    kwarg_format = match and match.group(1)
    if not kwarg_format:
        if not support_legacy:
            return {}
        if len(bits) < 3 or bits[1] != 'as':
            return {}

    kwargs = {}
    while bits:
        if kwarg_format:
            match = kwarg_re.match(bits[0])
            if not match or not match.group(1):
                return kwargs
            key, value = match.groups()
            del bits[:1]
        else:
            if len(bits) < 3 or bits[1] != 'as':
                return kwargs
            key, value = bits[2], bits[0]
            del bits[:3]
        kwargs[key] = parser.compile_filter(value)
        if bits and not kwarg_format:
            if bits[0] != 'and':
                return kwargs
            del bits[:1]
    return kwargs
