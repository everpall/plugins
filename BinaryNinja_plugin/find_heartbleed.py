import math
import sys
sys.path.append('C:\Users\sunghyun\Anaconda2\Lib\site-packages')
from binaryninja import (BinaryViewType, MediumLevelILInstruction,
                         MediumLevelILOperation, RegisterValueType,
                         SSAVariable)
from tqdm import tqdm
from z3 import (UGT, ULT, And, Array, BitVec, BitVecSort, Concat, Extract,
                LShR, Not, Or, Solver, ZeroExt, simplify, unsat)

# idea: assume byte swapping means that there will be 2+ assignments
# that must be a single byte. Each time an MLIL_SET_VAR_SSA operation
# is encountered, we can check if the value of that operation is constrained
# to 0 <= x <= 0xff.

COLOR = HighlightStandardColor.OrangeHighlightColor


def create_BitVec(ssa_var, size):
    return BitVec(
        '{}#{}'.format(
            ssa_var.var.name, ssa_var.version
        ),
        size * 8 if size else 1
    )

def SetColor(address):
    bb = bv.get_basic_blocks_at(address)
    bb[0].highlight = COLOR

def identify_byte(var, function):
    if isinstance(var, SSAVariable):
        possible_values = function[1].get_ssa_var_possible_values(var)
        size = function[function.get_ssa_var_definition(var)].size
    else:
        possible_values = var.possible_values
        size = var.size

    if (possible_values.type == RegisterValueType.UnsignedRangeValue and
            len(possible_values.ranges) == 1):
        value_range = possible_values.ranges[0]
        start = value_range.start
        end = value_range.end
        step = value_range.step

        for i in range(size):
            if (start, end, step) == (0, (0xff << (8 * i)), (1 << (8 * i))):
                return value_range



class ModelIsConstrained(Exception):
    pass

class BNILVisitor(object):
    def __init__(self, **kw):
        super(BNILVisitor, self).__init__()

    def visit(self, expression):
        method_name = 'visit_{}'.format(expression.operation.name)
        print '[*] method_name(visit) : ', method_name # ex : visit_MLIL_SET_VAR_SSA
        if hasattr(self, method_name):
            value = getattr(self, method_name)(expression)
        else:
            value = None
        return value

class ByteSwapModeler(BNILVisitor):
    def __init__(self, var, address_size, function):
        super(ByteSwapModeler, self).__init__()

        if (not isinstance(var, MediumLevelILInstruction) or
                var.operation != MediumLevelILOperation.MLIL_VAR_SSA):
            raise TypeError('var must be an MLIL_VAR_SSA operation')

        self.address_size = address_size
        self._memory = Array(
            'Memory',
            BitVecSort(address_size*8),
            BitVecSort(8)
        )
        self.solver = Solver()
        self.visited = set()
        self.to_visit = list()
        self.byte_values = dict()
        self.byte_vars = set()
        self.var = var
        self.function = var.function
        self.function_call = function

    def model_variable(self):
        var_def = self.function.get_ssa_var_definition(self.var.src)
        # Visit statements that our variable directly depends on
        self.to_visit.append(var_def)

        while self.to_visit:
            idx = self.to_visit.pop()
            print ''
            print '[+] get_ssa_var_definition : ', idx 
            print 'SSA form : ',  hex(idx.address), ' : ', idx
            print '[@]',self.function[idx]
            varLen = len(self.function[idx].vars_read)
            global ref 
            for i in range(0,varLen):
                arg = str(self.function[idx].vars_read[i].var)
                if arg.find('arg') is not -1:
            	        if len(arg_num) is 0: #Only 1 argument testing!
                            arg_num.append(arg.split('arg')[1]) 
                            print '[#] arg_num : ', arg_num[0]
                            print 'append arg_num list' , arg_num
                            ref = bv.get_code_refs(self.function_call.start)
                            print ref
                            for i in range(len(ref)):
                                if bv.get_disassembly(ref[0].address).find('call') is not 0:
                                    del ref[0]
                                    
            if idx is not None:
                if self.function[idx].operation.name is not "MLIL_VAR_PHI" :
                    SetColor(idx.address)
                self.visit(self.function[idx])
                

        # See if any constraints on the memcpy are directly influenced by
        # the variables that we know should be single bytes. This means
        # they likely constrain a potential byte swap.
        for i, branch in self.var.branch_dependence.iteritems():
            
            for vr in self.function[i].vars_read:
                #print "-----"
                #print self.function[i].vars_read
                if vr in self.byte_vars:
                    raise ModelIsConstrained()
                vr_def = self.function.get_ssa_var_definition(vr)
                if vr_def is None:
                    continue
                for vr_vr in self.function[vr_def].vars_read:
                    if vr_vr in self.byte_vars:
                        raise ModelIsConstrained

    def is_byte_swap(self):
        try:
            self.model_variable()
        except ModelIsConstrained:
            return False

        # Figure out if this might be a byte swap
        byte_values_len = len(self.byte_values)
        #print self.byte_values
        if 1 < byte_values_len <= self.var.src.var.type.width:
            var = create_BitVec(self.var.src, self.var.src.var.type.width)
           
            ordering = list(reversed([
                self.byte_values[x]
                for x in sorted(self.byte_values.keys())
            ]))

            reverse_var = Concat(
                *reversed([
                    Extract(i-1, i-8, var)
                    for i in range(len(ordering) * 8, 0, -8)
                ])
            )

            if len(ordering) < 4:
                reverse_var = Concat(
                    Extract(
                        31,
                        len(ordering)*8, var
                    ),
                    reverse_var
                )

            reversed_ordering = reversed(ordering)
            reversed_ordering = Concat(*reversed_ordering)

            # The idea here is that if we add the negation of this, if it's
            # not satisfiable, then that means there is no value such that
            # the equivalence does not hold. If that is the case, then this
            # should be a byte-swapped value.

            self.solver.add(
                Not(
                    And(
                        var == ZeroExt(
                            var.size() - len(ordering)*8,
                            Concat(*ordering)
                        ),
                        reverse_var == ZeroExt(
                            reverse_var.size() - reversed_ordering.size(),
                            reversed_ordering
                        )
                    )
                )
            )

            if self.solver.check() == unsat:
                return True

        return False

    def visit_MLIL_SET_VAR_SSA(self, expr):

        dest = create_BitVec(expr.dest, expr.size)

        src = self.visit(expr.src)

        # If this value can never be larger than a byte,
        # then it must be one of the bytes in our swap.
        # Add it to a list to check later.
        if src is not None and not isinstance(src, (int, long)):
            value_range = identify_byte(expr.src, self.function)
            if value_range is not None:
                self.solver.add(
                    Or(
                        src == 0,
                        And(src <= value_range.end, src >= value_range.step)
                    )
                )

                self.byte_vars.add(*expr.src.vars_read)

                if self.byte_values.get(
                    (value_range.end, value_range.step)
                ) is None:
                    self.byte_values[
                        (value_range.end, value_range.step)
                    ] = simplify(Extract(
                                int(math.floor(math.log(value_range.end, 2))),
                                int(math.floor(math.log(value_range.step, 2))),
                                src
                            )
                    )

        self.visited.add(expr.dest)
        if expr.instr_index in self.to_visit:
            self.to_visit.remove(expr.instr_index)

        if src is not None:
            self.solver.add(dest == src)

    def visit_MLIL_VAR_PHI(self, expr):
        # MLIL_VAR_PHI doesn't set the size field, so we make do
        # with this.
        dest = create_BitVec(expr.dest, expr.dest.var.type.width)

        phi_values = []

        for var in expr.src:
            if var not in self.visited:
                
                var_def = self.function.get_ssa_var_definition(var)
                #print '[PHI]',  hex(var_def.address), var_def
                self.to_visit.append(var_def)

            src = create_BitVec(var, var.var.type.width)

            # If this value can never be larger than a byte,
            # then it must be one of the bytes in our swap.
            # Add it to a list to check later.
            if src is not None and not isinstance(src, (int, long)):
                value_range = identify_byte(var, self.function)
                if value_range is not None:
                    self.solver.add(
                        Or(
                            src == 0,
                            And(
                                src <= value_range.end,
                                src >= value_range.step
                            )
                        )
                    )

                    self.byte_vars.add(var)

                    if self.byte_values.get(
                        (value_range.end, value_range.step)
                    ) is None:
                        self.byte_values[
                            (value_range.end, value_range.step)
                        ] = simplify(Extract(
                                    int(
                                        math.floor(
                                            math.log(value_range.end, 2)
                                        )
                                    ),
                                    int(
                                        math.floor(
                                            math.log(value_range.step, 2)
                                        )
                                    ),
                                    src
                                )
                        )

            phi_values.append(src)

        if phi_values:
            phi_expr = reduce(
                lambda i, j: Or(i, j), [dest == s for s in phi_values]
            )

            self.solver.add(phi_expr)

        self.visited.add(expr.dest)
        if expr.instr_index in self.to_visit:
            self.to_visit.remove(expr.instr_index)

    def visit_MLIL_VAR_SSA(self, expr):
        if expr.src not in self.visited:
            var_def = expr.function.get_ssa_var_definition(expr.src)
            
            if var_def is not None:
                self.to_visit.append(var_def)

        src = create_BitVec(expr.src, expr.size)

        value_range = identify_byte(expr, self.function)
        if value_range is not None:
            self.solver.add(
                Or(
                    src == 0,
                    And(src <= value_range.end, src >= value_range.step)
                )
            )

            self.byte_vars.add(expr.src)

        return src

    def visit_MLIL_OR(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left | right

    def visit_MLIL_AND(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left & right

    def visit_MLIL_LOAD_SSA(self, expr):
        src = self.visit(expr.src)

        if src is None:
            return

        memory = self._memory

        # we're assuming Little Endian for now
        if expr.size == 1:
            return memory[src]
        elif expr.size == 2:
            return Concat(memory[src+1], memory[src])
        elif expr.size == 4:
            return Concat(
                memory[src+3],
                memory[src+2],
                memory[src+1],
                memory[src]
            )
        elif expr.size == 8:
            return Concat(
                memory[src+7],
                memory[src+6],
                memory[src+5],
                memory[src+4],
                memory[src+3],
                memory[src+2],
                memory[src+1],
                memory[src]
            )

    def visit_MLIL_ZX(self, expr):
        src = self.visit(expr.src)

        if src is not None:
            return ZeroExt(
                (expr.size - expr.src.size) * 8,
                src
            )

    def visit_MLIL_ADD(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left + right

    def visit_MLIL_SUB(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left - right            

    def visit_MLIL_CONST(self, expr):
        return expr.constant

    def visit_MLIL_LSL(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left << right

    def visit_MLIL_LSR(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return LShR(left, right)

    def visit_MLIL_IF(self, expr):
        return self.visit(expr.condition)

    def visit_MLIL_CMP_E(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left == right

    def visit_MLIL_CMP_NE(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)

        if None not in (left, right):
            return left != right

    def visit_MLIL_CMP_ULT(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)
        if None not in (left, right):
            return ULT(left, right)

    def visit_MLIL_CMP_UGT(self, expr):
        left = self.visit(expr.left)
        right = self.visit(expr.right)
        if None not in (left, right):
            return UGT(left, right)

    def visit_MLIL_VAR_SSA_FIELD(self, expr):
        if expr.src not in self.visited:
            var_def = expr.function.get_ssa_var_definition(expr.src)
            if var_def is not None:
                self.to_visit.append(var_def)

        var = create_BitVec(expr.src, expr.src.var.type.width)

        field = Extract(
            ((expr.size + expr.offset) * 8) - 1,
            expr.offset * 8,
            var
        )

        return field

    def visit_MLIL_SET_VAR_SSA_FIELD(self, expr):
        # expr.size will be the width of the field, so we need the dest's real
        # width
        dest = create_BitVec(expr.dest, expr.dest.var.type.width)
        prev = create_BitVec(expr.prev, expr.prev.var.type.width)

        mask = (1 << (expr.size * 8) - 1) << (expr.offset * 8)

        mask = ~mask & ((1 << (expr.dest.var.type.width * 8)) - 1)

        src = self.visit(expr.src)

        self.visited.add(expr.dest)

        if expr.instr_index in self.to_visit:
            self.to_visit.remove(expr.instr_index)

        if src is not None:
            self.solver.add(
                dest == (
                    (prev & mask) | ZeroExt(
                            (
                                expr.dest.var.type.width -
                                (expr.size + expr.offset)
                            ) * 8,
                            (src << (expr.offset * 8))
                    )
                )
            )


def check_memcpy(memcpy_call, arg_num, function):
    size_param = memcpy_call.params[int(arg_num.pop(0))-1]
    ref =[]

    if size_param.operation != MediumLevelILOperation.MLIL_VAR_SSA:
        return False

    possible_sizes = size_param.possible_values

    # Dataflow won't combine multiple possible values from
    # shifted bytes, so any value we care about will be
    # undetermined at this point. This might change in the future?
    if possible_sizes.type != RegisterValueType.UndeterminedValue:
        return False

    model = ByteSwapModeler(size_param, bv.address_size, function)

    return model.is_byte_swap()


#------------Main Start!!----------------------

dangerous_calls = []
function_list = []

#Set Function Address
function = bv.get_function_at(0x1c00d0b0)
addr = 0x1c00de72
SetColor(addr)

arg_num = [3] # First function parameter location 
print 'Traced by Third({}) parameter '.format(arg_num[0])

#First Function Call!
print '<func name> ', function.name
function_list.append(function.name)
call_instr = function.get_low_level_il_at(addr).medium_level_il
check_memcpy(call_instr.ssa_form, arg_num, function)

print '*******************ref1*****************'
print ref
#Next Function Call!
while len(ref) is not 0 : 
    print '\n<func name> ', ref[0].function.name
    function_list.append(ref[0].function.name)
    print ref[0].function
    print '<address> : ', hex(ref[0].address)
    SetColor(ref[0].address)
    call_instr = ref[0].function.get_low_level_il_at(ref[0].address).medium_level_il
    check_memcpy(call_instr.ssa_form, arg_num, ref[0].function)


print '\n<Function Call stack>'
for i in range(len(function_list)):
	print function_list[i]

for call, func in dangerous_calls:
    print "****** POTENTIAL VULNERABILITY ******"
    print (
        "memcpy at 0x{:x} in {} uses a size parameter that potentially"
        " comes from an untrusted source!"
    ).format(
        call,
        bv.get_symbol_at(
            bv.get_functions_containing(func)[0].start
        ).name
    )

print 'Analysis complete.'