import ast

with open('gui.py') as f:
    source = f.read()

tree = ast.parse(source)

imports = {}
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            imports[name] = (node.module, node.lineno)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            imports[name] = (alias.name, node.lineno)

lines = source.split('\n')
unused = []
for name, (module, lineno) in sorted(imports.items()):
    count = 0
    for i, line in enumerate(lines, 1):
        if i == lineno:
            continue
        if name in line:
            count += 1
    if count == 0:
        unused.append((name, module, lineno))

print('=== UNUSED IMPORTS ===')
for name, module, lineno in unused:
    print(f'  Line {lineno}: "{name}" from "{module}"')
print(f'\nTotal: {len(unused)} unused imports out of {len(imports)} total')

# Also check for defined functions/methods never called
print('\n=== CHECKING FUNCTION DEFINITIONS vs CALLS ===')
# Get all function/method defs
defs = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defs.append((node.name, node.lineno))

# Check each function name usage elsewhere
for fname, lineno in sorted(defs, key=lambda x: x[1]):
    if fname.startswith('__'):  # skip dunder
        continue
    count = 0
    for i, line in enumerate(lines, 1):
        if i == lineno:
            continue
        if fname in line:
            count += 1
    if count == 0:
        print(f'  Line {lineno}: def {fname}() - never referenced elsewhere')
