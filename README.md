# deployer

A centralized serializing script runner.

`deployer` is a (`centralized`) server overseeing the execution of a set of
programs (for example shell scripts) and ensuring that the same program is
never run twice at the same time (`serializing`). Furthermore, the programs
are assumed to be “postidempotent”, _i.e._ that the result of a sequence of
invocations is equivalent to that of the *last* one; this is applicable to,
for example, well-behaved software deployment procedures, from which the
project name stems.
