# -*- coding: utf-8 -*-
import ast


def _parse_cls_function_body(funcBody):
    """Parse the content of a function in order to obtain class attributes."""
    attr = {}
    for at in funcBody:
        if type(at) is ast.Assign and \
        type(at.targets[0]) is ast.Attribute:
            attr[at.targets[0].attr] = at.targets[0].lineno
    return attr


def _parse_class_body(classBody):
    """Parse the content of a class to obtain the functions and attibutes."""
    attr = {}
    func = {}
    for sym in classBody:
        if type(sym) is ast.Assign:
            if type(sym.targets[0]) is ast.Attribute:
                attr[sym.targets[0].attr] = sym.targets[0].lineno
            elif type(sym.targets[0]) is ast.Name:
                attr[sym.targets[0].id] = sym.lineno
        elif type(sym) is ast.FunctionDef:
            func[sym.name] = sym.lineno
            moreAttr = _parse_cls_function_body(sym.body)
            for ma in moreAttr:
                attr[ma] = moreAttr[ma]
    return {'attributes': attr, 'functions': func}


def obtain_symbols(source):
    """Parse a module source code to obtain: Classes, Functions and Assigns."""
    compilable = True
    try:
        module = ast.parse(source)
    except:
        compilable = False
    if not compilable:
        try:
            module = ast.parse(source[source.find('\n'):])
            compilable = True
        except SyntaxError:
            compilable = False
    if not compilable:
        return {}
    symbols = {}
    globalAttributes = {}
    globalFunctions = {}
    classes = {}
    for sym1 in module.body:
        if type(sym1) is ast.Assign:
            if type(sym1.targets[0]) is ast.Attribute:
                globalAttributes[sym1.targets[0].attr] = sym1.lineno
            elif type(sym1.targets[0]) is ast.Name:
                globalAttributes[sym1.targets[0].id] = sym1.lineno
        elif type(sym1) is ast.FunctionDef:
            globalFunctions[sym1.name] = sym1.lineno
        elif type(sym1) is ast.ClassDef:
            classes[sym1.name] = (sym1.lineno, _parse_class_body(sym1.body))
    if globalAttributes:
        symbols['attributes'] = globalAttributes
    if globalFunctions:
        symbols['functions'] = globalFunctions
    if classes:
        symbols['classes'] = classes

    return symbols


def obtain_imports(source):
    compilable = True
    try:
        module = ast.parse(source)
    except:
        compilable = False
    if not compilable:
        try:
            module = ast.parse(source[source.find('\n'):])
            compilable = True
        except:
            compilable = False
    if not compilable:
        return []
    #Imports{} = {name: asname}, for example = {sys: sysAlias}
    imports = {}
    #From Imports{} = {name: {module: fromPart, asname: nameAlias}}
    fromImports = {}
    for sym in module.body:
        if type(sym) is ast.Import:
            for item in sym.names:
                imports[item.name] = item.asname
        if type(sym) is ast.ImportFrom:
            for item in sym.names:
                fromImports[item.name] = {'module': sym.module,
                    'asname': item.asname}
    return {'imports': imports, 'fromImports': fromImports}
