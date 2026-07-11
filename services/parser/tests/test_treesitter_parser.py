import pytest
from services.parser.treesitter_parser import parse_python_ast, parse_js_ts_ast

def test_parse_python_ast():
    content = """
import os
from sys import argv

async def do_something(x, y):
    pass

def normal_func():
    pass

class MyClass(BaseClass):
    pass
"""
    result = parse_python_ast(content)
    assert result["language"] == "python"
    assert "os" in result["dependencies"]
    assert "sys" in result["dependencies"]
    
    func_names = {f["name"] for f in result["functions"]}
    assert "do_something" in func_names
    assert "normal_func" in func_names
    
    async_funcs = [f for f in result["functions"] if f["async"]]
    assert len(async_funcs) == 1
    assert async_funcs[0]["name"] == "do_something"

    class_names = {c["name"] for c in result["classes"]}
    assert "MyClass" in class_names
    
    my_class = [c for c in result["classes"] if c["name"] == "MyClass"][0]
    assert my_class["extends"] == "BaseClass"


def test_parse_js_ast():
    content = """
const express = require('express');
import { something } from 'some-module';

class Service extends BaseService {}

async function doTask() {}
const arrowTask = async () => {}

export default Service;
export { doTask };

const app = express();
app.get('/api/test', (req, res) => res.json({}));
app.use(express.json());
"""
    result = parse_js_ts_ast(content, is_typescript=False)
    assert result["language"] == "javascript"
    
    assert "express" in result["dependencies"]
    assert "some-module" in result["dependencies"]
    
    func_names = {f["name"] for f in result["functions"]}
    assert "doTask" in func_names
    assert "arrowTask" in func_names
    
    class_names = {c["name"] for c in result["classes"]}
    assert "Service" in class_names
    
    service_class = [c for c in result["classes"] if c["name"] == "Service"][0]
    assert service_class["extends"] == "BaseService"
    
    assert "Service" in result["exports"]
    assert "doTask" in result["exports"]
    
    assert len(result["routes"]) == 1
    assert result["routes"][0]["method"] == "GET"
    assert result["routes"][0]["path"] == "/api/test"
    
    assert "express.json()" in result["middlewares"]

def test_parse_ts_ast():
    content = """
import { Server } from '@types/node';
class Controller {}
"""
    result = parse_js_ts_ast(content, is_typescript=True)
    assert result["language"] == "typescript"
    assert "@types/node" in result["dependencies"]
    assert result["classes"][0]["name"] == "Controller"
