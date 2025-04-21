from dataclasses import dataclass#用于简化类的定义
import rich#rich美化库
from rich.rule import Rule#创建水平分割横线，可以添加标题
from rich.text import Text#可以创建有样式的文本
from rich import print as rprint #重命名输出可以输出有样式的内容

# from rich.console import Console #管理在终端的输出

# RICH_CONSOLE = Console()#一个实例，rich终端


@dataclass#使用dataclass装饰器，这样ALogger类就会自动生成__init__、__repr__等方法
class Logger:
    prefix: str = ""#前缀

    def title(self, text: str | Text, rule_style="bright_blue"):
        '''输出带有指定前缀和标题的水平分隔线'''
        list = []#定义一个空列表来接受文本数据
        if self.prefix:#非空则为true
            list.append(rich.markup.escape(self.prefix))
        if text:#非空则为true
            list.append(text)
        rprint(Rule(title=" ".join(list), style=rule_style))

# def log_title(text: str | Text, rule_style="bright_blue"):
#     objs = []
#     if text:
#         objs.append(Rule(title=text, style=rule_style))
#     rprint(*objs)


if __name__ == "__main__":
    Logger().title("Hello World!")
