import types
import functools
import re
import sys
import os
import json
import pickle


class Controller():
    def __init__(self):
        self.commands = {}
        self.readmodes = {}
        self.writemodes = {}


class Settings():
    def __init__(self, source="settings.json"):
        self.tags = {}
        self.source = source

    def new(self, name, value, desc):
        self.tags[name] = [value, desc]

    def __getitem__(self, item):
        if self.tags.get(item):
            return self.tags[item][0]
        else:
            return None

    def desc(self, name):
        if self.tags.get(name):
            return self.tags[name][1]
        else:
            return None

    def save(self, target=None):
        if target is None:
            target = self.source
        if not isinstance(target, str):
            return False
        if not re.search(r".+\.json$", target):
            return False
        jsonwrite(self.tags, target)
        return True

    def load(self):
        if not isinstance(self.source, str):
            return False
        if not re.search(r".+\.json$", self.source):
            return False
        if not os.path.isfile(self.source):
            return False
        self.tags = jsonread(self.source)
        return True

    def change(self, tag, value):
        if not self.tags.get(tag):
            return False
        self.tags[tag][0] = value
        self.save()
        return True


class Bar():
    def __init__(self, total, current, prefix = "Progress", filler = '█'):
        self.total = total
        self.current = current
        self.prefix = prefix
        self.filler = filler
        self.prefix_len = len(prefix)

    def show(self):
        done = self.current / self.total * 100
        print(f"\r{self.prefix:{self.prefix_len}}: {done:6.2f}% |" + (int(done) * self.filler) + \
              ((100 - int(done)) * '-') + '|', end='\r')

    def next(self, steps = 1):
        self.current += steps
        self.show()

    def new_prefix(self, prefix):
        self.prefix_len = max(self.prefix_len, len(prefix))
        self.prefix = prefix

    def end(self):
        print()


controller= Controller()


def add_to_switch(_func: types.FunctionType = None,* , switch: dict = None, name: str = None) -> types.FunctionType:
    """
    Adds function to pointed switch
    :param _func: Any not built-in python function.
    :type _func: types.FunctionType or None
    :param dict switch:
    :param name:
    :type name: str or None
    :return: input function
    :rtype: types.FunctionType
    :raises TypeError: if any of given arguments is of the wrong type
    """
    def decorator_add_to_switch(func: types.FunctionType) -> types.FunctionType:
        if not isinstance(switch, dict):
            raise TypeError(f"Switch must be a dictionary, not a {type(switch)}.")
        if name is None:
            switch[func.__name__] = func
        elif isinstance(name, str):
            switch[name] = func
        else:
            raise TypeError(f"Name must be a string, not a {type(name)}.")
        return func
    if _func is None:
        return decorator_add_to_switch
    else:
        return decorator_add_to_switch(_func)


def correctness(func: types.FunctionType) -> types.FunctionType:
    """
    Checks if all args and kwargs are of the right type (Function must have annotations for this to work)
    :param types.FunctionType func:
    :return:
    :rtype: types.FunctionType
    """
    @functools.wraps(func)
    def wrapper_correctness(*args, **kwargs):
        checklist = {arg: 0 for arg in func.__annotations__}
        if checklist.get("return") is not None:
            checklist["return"] = 1
        for kwarg in kwargs:
            if (_type := func.__annotations__.get(kwarg)) is None:
                return f"{func.__name__} got an unexpected argument {kwarg}"
            if not isinstance(kwargs[kwarg], _type):
                return f"{func.__name__} {kwarg} must be a {_type}, not a {type(kwargs[kwarg])}."
            checklist[kwarg] = 1
        else:
            if func.__kwdefaults__ is not None:
                for kwarg in func.__kwdefaults__:
                    checklist[kwarg] = 1
            counter = 0
            for arg in checklist:
                if checklist[arg] == 1:
                    continue
                if counter >= len(args):
                    return f"{func.__name__}, missing argument {arg}"
                if not isinstance(args[counter], func.__annotations__[arg]):
                    return f"{func.__name__} {arg} must be a {func.__annotations__[arg]}, not a {type(args[counter])}"
                counter += 1
            else:
                if counter == len(args):
                    if (result := func(*args, **kwargs)) is not None:
                        return result
                    else:
                        return f"Inner fucntion {func.__name__} should return a completion information"
                else:
                    return f"{func.__name__}, too many arguments were given"
    return wrapper_correctness


def io_files(_func: types.FunctionType = None, *, source: str = None, target: str = None):
    """
    Makes algorythm use data from source and save it to target.
    :param types.FunctionType _func:
    :param str source: source file
    :param str target: target file
    :return: decorated function
    :rtype: types.FunctionType
    """
    def decorator_iofiles(func):
        @functools.wraps(func)
        def wrapper_iofiles(*args, **kwargs):
            if not os.path.isfile(source):
                print("Generate or enter the data first.")
                return
            if (_type := re.search("\.[A-z]+", source)) is None:
                raise ValueError("File without extension")
            if controller.readmodes.get(_type.group()) is None:
                raise ValueError(f"{_type.group()} extension is not available")
            data = controller.readmodes[_type.group()](source)
            result = []
            message = func(data, result, *args, **kwargs)
            if target is not None:
                if (_type := re.search("\.[A-z]+", target)) is None:
                    raise ValueError("File without extension")
                if controller.writemodes.get(_type.group()) is None:
                    raise ValueError(f"{_type.group()} extension is not available")
                controller.writemodes[_type.group()](result, target)
            return message
        return wrapper_iofiles
    if _func is None:
        return decorator_iofiles
    else:
        return decorator_iofiles(_func)


def availability(_func: types.FunctionType = None, *, switch: dict, name: str):
    """
    Extends docstring of the func
    :param types.FunctionType _func:
    :param dict switch:
    :param str name:
    :return:
    """
    def decorator_availability(func):
        func.__doc__ += f"Available {name}:"
        for thing in switch:
            func.__doc__ += f"\n\t+ {thing:10}"
            if switch[thing].__doc__ is not None:
                func.__doc__ += f" -> {switch[thing].__doc__}"
        return func
    if _func is None:
        return decorator_availability
    else:
        return decorator_availability(_func)


@add_to_switch(switch=controller.readmodes, name=".pkl")
def pklread(source: str):
    """
    Reads from pkl file
    :param str source:
    :return:
    """
    with open(source, "rb") as origin:
        result = pickle.load(origin)
    return result


@add_to_switch(switch=controller.readmodes, name=".json")
def jsonread(source: str):
    """
    Reads from json file
    :param str source:
    :return:
    """
    with open(source, "r") as origin:
        result = json.load(origin)
    return result


@add_to_switch(switch=controller.writemodes, name=".pkl")
def pklwrite(object, target: str):
    """
    Writes to pkl file
    :param object:
    :param str target:
    :return:
    """
    with open(target, "wb") as goal:
        pickle.dump(object, goal)


@add_to_switch(switch=controller.writemodes, name=".json")
def jsonwrite(object, target: str):
    """
    Writes to json file
    :param object:
    :param str target:
    :return:
    """
    with open(target, "w") as goal:
        json.dump(object, goal)


@add_to_switch(switch=controller.commands, name="list")
@correctness
def clist() -> str:
    """
    Used to generate list of available commands
    :param Controller controller:
    :return: result
    :rtype: str
    """
    result = ["Available commands:"]
    for command in controller.commands:
        desc = ""
        if controller.commands[command].__doc__ is not None:
            pointer = controller.commands[command].__doc__.find('\n', 1)
            desc = controller.commands[command].__doc__[1:pointer:]
        result.append(f"\t+ {command:20} -> {desc}")
    result.append("Type help [command_name] to get more info about specific command")
    return "\n".join(result)


@add_to_switch(switch=controller.commands, name="exit")
@correctness
def cexit():
    """
    Terminates the process
    :param Controller controller:
    :return:
    """
    print("Process terminated")
    sys.exit()


@add_to_switch(switch=controller.commands, name="help")
@correctness
def chelp(command: str = None) -> str:
    """
    Shows documentation of the chosen command
    :param Controller controller:
    :param command: User specified
    :type command: None or str
    :return:
    :rtype: str
    """
    result = ""
    if command is None:
        return "Type help [command_name] to get more info about specific command"
    elif (func := controller.commands.get(command)) is not None:
        result += f"{command} command\n"
        result += "Usage: command params separated with single space"
        result += func.__doc__
        return result
    else:
        return f"Command {command} is not an available command, type list to see the list of available commands"


@add_to_switch(switch=controller.commands, name="clear")
@correctness
def cclear():
    """
    Clear the screen
    :param Controller controller:
    :return:
    """
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")
    return "\n"


def detector(charray: str):
    """
    Convert string to int or list if possible
    :param str charray:
    :return:
    """
    if charray == "False":
        return False
    if charray == "True":
        return True
    if re.match("\[([0-9]+,)*[0-9]+\]", charray):
        arr = [int(i) for i in re.findall("[0-9]+", charray)]
        return arr
    if re.match("^[0-9]+$", charray):
        return int(charray)
    else:
        return charray


def main():
    """
    Terminal handler
    :param Controller controller:
    :return:
    """
    print("Type list to show available commands")
    while True:
        print(">> ", end="")
        data = input().strip().split()
        for i in range(len(data)-1, -1, -1):
            if data[i] == " ":
                del data[i]
        if len(data) == 0:
            continue
        kwarguments = {}
        for i in range(len(data) - 1, -1, -1):
            if match := re.match("^_.$", data[i]):
                del data[i]
                try:
                    kwarguments[match.string] = detector(data[i])
                    del data[i]
                except KeyError:
                    print(f"{match.string} value not found.")
        command, *arguments = data
        arguments = [detector(argument) for argument in arguments]
        if (func := controller.commands.get(command.lower())) is not None:
            print(func(*arguments, **kwarguments), '\n')
        else:
            print(f"{command} is not a defined command")


if __name__ == "__main__":
    main()