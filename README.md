# deployer

A centralized serializing script runner.

`deployer` is a (`centralized`) server overseeing the execution of a set of
programs (for example shell scripts) and ensuring that the same program is
never run twice at the same time (`serializing`). Furthermore, the programs
are assumed to be “postidempotent”, _i.e._ that the result of a sequence of
invocations is equivalent to that of the *last* one; this is applicable to,
for example, well-behaved software deployment procedures, from which the
project name stems.

## Usage

`deployer` accepts the following command-line arguments:

  - `-s` *path*, `--socket` *path* — *Communication socket location*: Where
    to bind the (UNIX domain) socket used by clients to access `deployer`.
  - `-m` *mode*, `--mode` *mode* — *Socket access mode*: Which access bits to
    set on the socket. May be useless as an access restriction on some
    platforms.
  - `-r` *path*, `--root` *path* — *Script directory*: Where the programs to
    be run are located.

Scripts must be located directly inside `root` and be have the executable bit
set to be run successfully.

## Communication

A session of some client with `deployer` looks as follows:

 1. The client connects to the communication socket.
 2. The client sends a line consisting of the string `RUN` followed by a
    space and the name of the program to run. **Note** that there is no way
    of passing arguments.
 3. The server replies with a line consisting of:
      - `OK`: The script was found and will run immediately.
      - `OK WAIT`: The script was found, but is already running. This request
        will either run later or not at all if another client requests it
        before the instance running in the background finishes.
      - `ERROR <message>`: Some stage of preparing to run the script failed;
        the `<message>` contains a short explanation of the error.
 4. If the script actually runs, the server relays any output (both standard
    output and standard error) from the script to the client and any data
    received from the client to the script's standard input.
 5. Once the script finishes running `deployer` shuts down the corresponding
    half of the connection to let the client know the script is done. As the
    script may close its standard output otherwise, still sending data may
    or may not make sense.
 6. Finally, the client closes the connection.

In particular, the protocol is extremely simple; the following one-liner

    echo "RUN sample.sh" | nc -U /var/run/deployer | tail -n+2

runs `sample.sh` and forwards its output to the console. Note that `tail`
may buffer its output if it is fed into a pipeline.
