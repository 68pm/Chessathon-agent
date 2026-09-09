"""Reuse separate move/score storage at each search ply, preserving move logic."""
import ast
import copy


def transform(source):
    tree=ast.parse(source)
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    generation=copy.deepcopy(functions['generate'])
    generation.name='generate_buffered'
    generation.args.args.append(ast.arg(arg='storage'))
    generation.args.defaults=[]
    assert ast.unparse(generation.body[0])=='moves = np.empty(256, dtype=np.int64)'
    generation.body[0]=ast.parse('moves = storage').body[0]

    class GuardWrites(ast.NodeTransformer):
        def visit_Assign(self,node):
            if len(node.targets)==1 and ast.unparse(node.targets[0])=='moves[n]':
                return [ast.parse("assert n < len(moves), 'Move storage exhausted'").body[0],node]
            return node

    generation=GuardWrites().visit(generation)
    ordering=copy.deepcopy(functions['order_moves'])
    ordering.name='order_moves_buffered'
    ordering.args.args.append(ast.arg(arg='storage'))
    assert ast.unparse(ordering.body[0])=='scores = np.empty(len(moves), dtype=np.int64)'
    ordering.body[:1]=ast.parse("assert len(storage) >= len(moves), 'Score storage exhausted'\nscores = storage[:len(moves)]").body
    index=tree.body.index(functions['search'])
    tree.body[index:index]=[generation,ordering]

    class Calls(ast.NodeTransformer):
        def __init__(self,inside_search):
            self.inside_search=inside_search
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if not isinstance(node.func,ast.Name):
                return node
            if node.func.id=='search':
                node.args.extend([ast.Name(id='move_storage',ctx=ast.Load()),ast.Name(id='score_storage',ctx=ast.Load())])
            elif self.inside_search and node.func.id in ('generate','order_moves'):
                storage='move_storage' if node.func.id=='generate' else 'score_storage'
                node.func.id+='_buffered'
                node.args.append(ast.parse(storage+'[ply]',mode='eval').body)
            return node

    for name in ('search','root_iteration'):
        function=functions[name]
        function.args.args.extend([ast.arg(arg='move_storage'),ast.arg(arg='score_storage')])
        Calls(name=='search').visit(function)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def transform_driver(source):
    old='        self.nodes = 0'
    assert source.count(old)==1
    source=source.replace(old,'        self.move_storage = np.empty((100, 512), dtype=np.int64)\n'
        '        self.score_storage = np.empty((100, 512), dtype=np.int64)\n'+old)
    old='                self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions)'
    assert source.count(old)==1
    source=source.replace(old,'                self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions,\n'
        '                self.move_storage, self.score_storage)')
    return source
