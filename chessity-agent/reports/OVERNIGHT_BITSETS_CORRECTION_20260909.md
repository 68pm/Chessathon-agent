The first bitset correctness run failed LLVM verification: ctlz requires an
immediate boolean flag. A comparison that always evaluates false is not a literal
constant at verification time. All15 failures came through that intrinsic;
3other tests passed. No search measurements or games ran. Preserve bitsets-01.

For bitsets-02 use Numba context.get_constant(types.boolean, False), whose native
BooleanModel value type is i1. Keep all chess logic, tests and declared performance
gates identical. Use the existing package-compatible relative-module import form
and explicit dispatcher aliases. Do not alter the submission dependency allowlist.
Run the same real compiled tests again before launching any benchmarks.
