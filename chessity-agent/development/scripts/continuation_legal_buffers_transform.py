"""Reuse an existing per-ply buffer in full legal-existence checks."""
import ast
import copy


def transform(source):
    tree=ast.parse(source)
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    assert 'has_legal_move_buffered' not in functions
    helper=copy.deepcopy(functions['has_legal_move'])
    helper.name='has_legal_move_buffered'
    helper.args.args.append(ast.arg(arg='storage'))
    class Generation(ast.NodeTransformer):
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='generate':
                assert len(node.args)==2 and not node.keywords
                node.func.id='generate_buffered'
                node.args += [ast.Constant(value=False),ast.Name(id='storage',ctx=ast.Load())]
            return node
    helper=Generation().visit(helper)
    index=tree.body.index(functions['search'])
    tree.body.insert(index,helper)
    class LegalCalls(ast.NodeTransformer):
        def __init__(self):self.count=0
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='has_legal_move':
                node.func.id='has_legal_move_buffered'
                node.args.append(ast.parse('move_storage[ply]',mode='eval').body)
                self.count+=1
            return node
    calls=LegalCalls()
    calls.visit(functions['search'])
    assert calls.count==3
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'
