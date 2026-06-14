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
