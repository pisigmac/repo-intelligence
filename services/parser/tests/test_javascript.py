from pathlib import Path
from services.parser.javascript import parse_javascript


TS_SAMPLE = '''
import { useState } from 'react';
import supabase from './lib/supabase';

export function Dashboard() {
  return <div>Hello</div>;
}

export class PetStore {
  constructor(public name: string) {}
}

const handler = async (req: Request) => {
  return new Response('ok');
};
'''


def test_typescript_functions_and_classes():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    names = {f["name"] for f in result["functions"]}
    assert "Dashboard" in names
    assert "handler" in names
    class_names = {c["name"] for c in result["classes"]}
    assert "PetStore" in class_names


def test_typescript_dependencies():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    assert "react" in result["dependencies"]
    assert "./lib/supabase" in result["dependencies"]


def test_typescript_lines_of_code():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    assert result["lines_of_code"] > 0


ANONYMOUS_CALLBACK_SAMPLE = '''
const express = require('express');
const app = express();

app.get('/', function (req, res) {
  res.send('hello');
});

app.post('/json', (req, res) => {
  res.json({ ok: true });
});
'''


def test_anonymous_functions_and_arrow_callbacks():
    result = parse_javascript(Path("routes/index.js"), ANONYMOUS_CALLBACK_SAMPLE)
    anon_types = {f["type"] for f in result["functions"]}
    assert "anonymous_function" in anon_types
    assert "arrow_function" in anon_types


DECORATOR_SAMPLE = '''
import { Controller, Get, Post, Body } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Get()
  findAll(): string {
    return 'This action returns all cats';
  }

  @Post()
  create(@Body() createCatDto: CreateCatDto) {
    return 'This action adds a new cat';
  }
}
'''


def test_typescript_class_decorators():
    result = parse_javascript(Path("cats.controller.ts"), DECORATOR_SAMPLE)
    classes = result["classes"]
    assert len(classes) == 1
    assert classes[0]["name"] == "CatsController"
    assert "Controller" in classes[0].get("decorators", [])


def test_typescript_method_decorators():
    result = parse_javascript(Path("cats.controller.ts"), DECORATOR_SAMPLE)
    method_decorators = set()
    for f in result["functions"]:
        method_decorators.update(f.get("decorators", []))
    assert "Get" in method_decorators
    assert "Post" in method_decorators
