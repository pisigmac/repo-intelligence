import tree_sitter
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript

py_lang = tree_sitter.Language(tree_sitter_python.language(), "python")
js_lang = tree_sitter.Language(tree_sitter_javascript.language(), "javascript")
ts_lang = tree_sitter.Language(tree_sitter_typescript.language_typescript(), "typescript")

py_parser = tree_sitter.Parser()
py_parser.set_language(py_lang)

js_parser = tree_sitter.Parser()
js_parser.set_language(js_lang)

ts_parser = tree_sitter.Parser()
ts_parser.set_language(ts_lang)


def parse_python_ast(content: str) -> dict:
    tree = py_parser.parse(content.encode("utf-8"))
    
    # Queries
    query_funcs = py_lang.query("""
        (function_definition 
            name: (identifier) @func_name
            parameters: (parameters) @params) @func_def
    """)
    query_classes = py_lang.query("""
        (class_definition 
            name: (identifier) @class_name
            superclasses: (argument_list)? @superclasses) @class_def
    """)
    query_imports = py_lang.query("""
        (import_statement (dotted_name) @module)
        (import_from_statement module_name: (dotted_name) @module)
    """)
    
    functions = []
    for node, capture_name in query_funcs.captures(tree.root_node):
        if capture_name == "func_def":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            if name_node:
                is_async = node.children[0].type == "async" if node.children else False
                params_text = params_node.text.decode("utf-8") if params_node else "()"
                functions.append({
                    "name": name_node.text.decode("utf-8"),
                    "signature": f"{name_node.text.decode('utf-8')}{params_text}",
                    "async": is_async
                })
                
    classes = []
    for node, capture_name in query_classes.captures(tree.root_node):
        if capture_name == "class_def":
            name_node = node.child_by_field_name("name")
            superclasses_node = node.child_by_field_name("superclasses")
            if name_node:
                extends_text = None
                if superclasses_node:
                    # superclasses_node text is like (BaseClass)
                    text = superclasses_node.text.decode("utf-8")
                    if text.startswith("(") and text.endswith(")"):
                        extends_text = text[1:-1]
                classes.append({
                    "name": name_node.text.decode("utf-8"),
                    "extends": extends_text
                })
                
    dependencies = []
    for node, capture_name in query_imports.captures(tree.root_node):
        if capture_name == "module":
            dependencies.append(node.text.decode("utf-8").split(".")[0])
            
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    
    return {
        "language": "python",
        "lines_of_code": loc,
        "functions": functions,
        "classes": classes,
        "dependencies": list(set(dependencies)),
    }


def parse_js_ts_ast(content: str, is_typescript: bool = False) -> dict:
    lang = ts_lang if is_typescript else js_lang
    parser = ts_parser if is_typescript else js_parser
    tree = parser.parse(content.encode("utf-8"))
    
    # Shared JS/TS queries
    query_funcs = lang.query("""
        (function_declaration name: (identifier) @func_name parameters: (formal_parameters) @params) @func_def
        (method_definition name: (property_identifier) @func_name parameters: (formal_parameters) @params) @method_def
        (lexical_declaration (variable_declarator name: (identifier) @func_name value: (arrow_function parameters: (formal_parameters) @params) @arrow_val)) @arrow_def
    """)
    
    query_classes = lang.query("""
        (class_declaration name: (identifier) @class_name (class_heritage (identifier) @superclass)?) @class_def
    """)
    
    query_imports = lang.query("""
        (import_statement source: (string (string_fragment) @import_path))
        (call_expression function: (identifier) @req_id arguments: (arguments (string (string_fragment) @require_path))
         (#eq? @req_id "require"))
    """)
    
    query_exports = lang.query("""
        (export_statement (identifier) @export_name)
        (export_statement (export_clause (export_specifier (identifier) @export_name)))
        (export_statement declaration: (function_declaration name: (identifier) @export_name))
        (export_statement declaration: (class_declaration name: (identifier) @export_name))
        (export_statement declaration: (lexical_declaration (variable_declarator name: (identifier) @export_name)))
    """)
    
    functions = []
    # Process functions, methods, arrow functions
    for node, capture_name in query_funcs.captures(tree.root_node):
        if capture_name in ["func_def", "method_def", "arrow_def"]:
            name = None
            params_text = "()"
            is_async = False
            if capture_name == "func_def" or capture_name == "method_def":
                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("parameters")
                if name_node: name = name_node.text.decode("utf-8")
                if params_node: params_text = params_node.text.decode("utf-8")
                if node.children and node.children[0].type == "async": is_async = True
            elif capture_name == "arrow_def":
                # For lexical declaration, find declarator
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        if name_node: name = name_node.text.decode("utf-8")
                        arrow_node = child.child_by_field_name("value")
                        if arrow_node and arrow_node.type == "arrow_function":
                            if arrow_node.children and arrow_node.children[0].type == "async": is_async = True
                            params_node = arrow_node.child_by_field_name("parameters")
                            if params_node: params_text = params_node.text.decode("utf-8")
            
            if name:
                functions.append({
                    "name": name,
                    "signature": f"{name}{params_text}",
                    "async": is_async
                })
                
    classes = []
    for node, capture_name in query_classes.captures(tree.root_node):
        if capture_name == "class_def":
            name_node = node.child_by_field_name("name")
            if name_node:
                extends = None
                heritage_node = node.child_by_field_name("heritage")
                if heritage_node:
                    extends = heritage_node.text.decode("utf-8").replace("extends ", "").strip()
                classes.append({
                    "name": name_node.text.decode("utf-8"),
                    "extends": extends
                })
                
    dependencies = []
    for node, capture_name in query_imports.captures(tree.root_node):
        if capture_name in ["import_path", "require_path"]:
            path = node.text.decode("utf-8")
            if not path.startswith("."):
                # Handle scoped packages @org/pkg
                parts = path.split("/")
                if path.startswith("@") and len(parts) >= 2:
                    dependencies.append(f"{parts[0]}/{parts[1]}")
                elif parts:
                    dependencies.append(parts[0])
                    
    exports = []
    for node, capture_name in query_exports.captures(tree.root_node):
        if capture_name == "export_name":
            exports.append(node.text.decode("utf-8"))
            
    # For routes and middlewares, regex is usually simpler because tree-sitter queries for all express variations can be very complex.
    # However, since they were previously supported in JS, we should migrate them or keep regex for just routes/middlewares.
    # I will extract routes and middlewares using regex just as a fallback since express patterns are very dynamic.
    import re
    routes = []
    for match in re.finditer(r'''(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]''', content):
        routes.append({"method": match.group(1).upper(), "path": match.group(2)})
        
    middlewares = []
    for match in re.finditer(r"(?:app|router)\.use\s*\(\s*([^)]+)\)", content):
        middlewares.append(match.group(1).strip())
        
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])
    
    return {
        "language": "typescript" if is_typescript else "javascript",
        "lines_of_code": loc,
        "functions": functions,
        "classes": classes,
        "dependencies": list(set(dependencies)),
        "exports": list(set(exports)),
        "routes": routes,
        "middlewares": middlewares,
    }
