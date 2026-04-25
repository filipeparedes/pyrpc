# pyrpc — Technical Manual

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Communication Protocol](#communication-protocol)
3. [Server](#server)
4. [Client](#client)
5. [Module: calculations.py](#module-calculationspy)
6. [Module: encryption.py](#module-encryptionpy)
7. [Tests](#tests)

---

## Architecture Overview

pyrpc follows a client-server architecture over raw TCP sockets. The server exposes a set of registered functions that clients can invoke remotely using the JSON-RPC 2.0 protocol.

```
┌─────────────────────┐         TCP + JSON-RPC 2.0          ┌──────────────────────────┐
│     RPCClient       │  ─────────────────────────────────► │       RPCServer          │
│                     │ ◄─────────────────────────────────  │                          │
│  - invoke()         │                                     │  - handle_request()      │
│  - dynamic_menu()   │                                     │  - client_thread()       │
│  - __enter/exit__() │                                     │  - register_functions()  │
└─────────────────────┘                                     └──────────┬───────────────┘
                                                                       │
                                                         ┌─────────────┴──────────────┐
                                                         │                            │
                                                 ┌───────┴─────────┐     ┌────────────┴───────┐
                                                 │ calculations.py │     │   encryption.py    │
                                                 │                 │     │                    │
                                                 │  Prime numbers  │     │  RSA, crack_key    │
                                                 └─────────────────┘     └────────────────────┘
```

The server handles each client connection in a separate thread, allowing multiple clients to connect and make requests concurrently. Functions from `calculations.py` and `encryption.py` are automatically discovered and registered at server startup.

---

## Communication Protocol

The server and client communicate over TCP using **newline-delimited JSON messages** — each message is a valid JSON string terminated by `\n`.

This delimiter approach solves the TCP framing problem: since TCP is a stream protocol with no built-in message boundaries, using `\n` as a separator allows the receiver to accumulate chunks until a complete message arrives.

### Single Request

```json
{
  "jsonrpc": "2.0",
  "method": "next_prime",
  "params": [97],
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Single Response

```json
{
  "jsonrpc": "2.0",
  "result": 101,
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Batch Request

Multiple requests can be sent in a single message as a JSON array:

```json
[
  {"jsonrpc": "2.0", "method": "next_prime", "params": [10], "id": "1"},
  {"jsonrpc": "2.0", "method": "is_prime", "params": [17], "id": "2"}
]
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "error": { "code": -32601, "message": "Method not found" },
  "id": "1"
}
```

### Error Codes

| Code | Meaning |
|---|---|
| `-32700` | Parse error — invalid JSON |
| `-32600` | Invalid request — missing or malformed fields |
| `-32601` | Method not found |
| `-32603` | Internal error — exception raised during function execution |

### Parameter Passing

Functions can be called with positional or keyword arguments:

- **Positional** — `params` is a JSON array: `[1, 2, 3]`
- **Keyword** — `params` is a JSON object: `{"n": 97}`
- **Mixed** — `params` is a JSON object with a special `__args__` key for positional arguments: `{"__args__": [1, 2], "timeout": 5}`

---

## Server

**File:** `src/rpc_server.py`

### Class: `RPCServer`

#### `__init__(host, port)`

Initializes the server with the given host and port. Sets up internal state: function registry (`self.funcs`), thread lock, client counter, and shutdown flag. Calls `register_functions()` automatically.

#### `register_functions()`

Iterates over all public functions (those not prefixed with `_`) in `calculations` and `encryption` using Python's `inspect` module, and registers each one via `register()`.

#### `register(name, func)`

Adds a function to the registry under the given name. Logs the registration.

#### `list_functions()`

Returns a list of all registered functions, each with its name, parameter list (including default values), and docstring. This is exposed as a remote method so clients can discover available functions at runtime.

#### `make_response(result, error, id)`

Constructs a valid JSON-RPC 2.0 response object. Includes either `result` or `error`, never both.

#### `handle_single_request(req)`

Processes one JSON-RPC request dictionary. Validates the `jsonrpc` version and `method` fields, dispatches to the correct function, and handles positional, keyword and mixed arguments. Returns a response object.

Note: when `__args__` is present in params, a copy of the dictionary is made before popping to avoid mutating the original.

#### `handle_request(request_json)`

Entry point for incoming data. Parses the JSON string and delegates to `handle_single_request()` for single requests, or iterates over the array for batch requests. Catches JSON parse errors and returns the appropriate error response.

#### `client_thread(conn, addr)`

Runs in a dedicated thread for each connected client. Reads data into a buffer and processes complete messages as they arrive (delimited by `\n`). Decrements the active client counter when the connection closes.

#### `start()`

Binds the server socket and enters the accept loop. Each incoming connection spawns a new thread via `client_thread()`. Uses a 1-second socket timeout to periodically check the shutdown flag. After shutdown is requested, waits for all active client threads to finish before exiting.

---

## Client

**File:** `src/rpc_client.py`

### Class: `RPCClient`

#### `__init__(host, port)`

Creates a TCP socket and connects to the server immediately on instantiation.

#### `__getattr__(attr)`

Intercepts any attribute access that doesn't exist on the object and returns a callable that invokes the corresponding remote method. This allows calling remote functions as if they were local methods:

```python
client.next_prime(97)  # calls invoke("next_prime", (97,))
```

#### `invoke(function, arguments)`

Builds a JSON-RPC 2.0 request with a random UUID as `id`, sends it over the socket terminated by `\n`, and reads the response by accumulating chunks until `\n` is received. Parses and returns the result, or raises `AttributeError` on error.

#### `dynamic_menu()`

Fetches the list of available functions from the server via `list_functions` and presents an interactive terminal menu. Handles both mandatory and optional parameters, using `ast.literal_eval` to parse typed input into the correct Python types. Loops until the user selects `0` to exit.

#### `close()`

Closes the socket and sets it to `None`.

#### `__enter__()` / `__exit__()`

Implements the context manager protocol, allowing the client to be used with `with`:

```python
with RPCClient() as client:
    client.dynamic_menu()
```

`__exit__` calls `close()` automatically, ensuring the connection is always released.

---

## Module: calculations.py

**File:** `src/utils/calculations.py`

All functions in this module are automatically registered on the server and available for remote invocation.

### `is_prime(n)`

Checks primality using the **6k ± 1 optimization**: after handling small cases (≤ 3) and divisibility by 2 and 3, only tests divisors of the form `6k ± 1` up to `√n`. This reduces the number of checks by roughly two thirds compared to a naive trial division.

### `next_prime(n)` / `previous_prime(n)`

Iterates forward or backward from `n` using `is_prime()`. `previous_prime` returns `None` if no prime is found before 2.

### `prime_factors(n)`

Trial division starting from 2, testing all integers up to `√n`. Each found factor is appended and `n` is reduced. Any remainder greater than 1 after the loop is itself a prime factor.

### `find_next_twin_primes(n)`

Iterates from `n+1` upward, checking each pair `(i, i+2)` for primality. Returns the first such pair where both are prime.

### `is_mersenne_prime(n)`

A Mersenne prime has the form `2^p - 1` where `p` is prime. The function computes `p = log₂(n+1)` and verifies that `p` is an integer, that `p` is prime, and that `n` itself is prime.

### `find_max_prime_sequential(timeout)`

Iterates through all integers starting from 2, tracking the last prime found, until the timeout expires. Returns the largest prime found.

### `find_max_prime_parallel(timeout)`

Distributes the search across all available CPU cores using `multiprocessing`. Each worker starts at a different odd number and steps by `2 * num_workers` to avoid overlap. Workers share a `Value` for the current maximum and a `Lock` for safe updates. All processes are joined after the timeout.

---

## Module: encryption.py

**File:** `src/utils/encryption.py`

### `_generate_large_prime(bits)` *(internal)*

Generates a random odd integer of the specified bit length with the most significant bit set (to guarantee size), then tests it with `is_prime()`. Repeats until a prime is found.

### `generate_keys(bits)`

Generates an RSA key pair:

1. Generates two distinct large primes `p` and `q` of `bits/2` bits each
2. Computes `n = p * q` and `φ(n) = (p-1)(q-1)`
3. Uses `e = 65537` as the public exponent, incrementing by 2 if not coprime with `φ(n)`
4. Computes `d = e⁻¹ mod φ(n)` using Python's built-in modular inverse (`pow(e, -1, phi)`)
5. Returns `(n, e)` as the public key and `(n, d)` as the private key

### `encrypt(message, pub_key)`

Computes `ciphertext = message^e mod n` using Python's built-in `pow(message, e, n)`. Raises `ValueError` if the message is not in the range `(0, n)`.

### `decrypt(ciphertext, priv_key)`

Computes `message = ciphertext^d mod n`.

### `_try_factors(n, start, step, found_flag, result)` *(internal)*

Worker function for parallel key cracking. Performs trial division starting at `start`, incrementing by `step`, up to `√n`. On finding a factor, sets a shared `found_flag` and writes the result to a shared `Array`. Checks the flag on each iteration to exit early if another worker already found a solution.

### `crack_key(n, e, timeout)`

Attempts to recover the private key from a public key `(n, e)` by factoring `n`:

1. Spawns one worker process per CPU core, each exploring a different subset of divisors
2. Waits up to `timeout` seconds, polling `found_flag`
3. Terminates all workers after timeout or on success
4. If factors `p` and `q` are found, recomputes `φ(n)` and `d`, then validates the result by encrypting and decrypting a test value (`42`)
5. Returns `(n, d)` if valid, otherwise `None`

This approach is effective for small keys (≤ 32 bits) but infeasible for production-grade RSA keys.

---

## Tests

**File:** `tests/tests.py`

The test suite uses `pytest` and covers both unit tests on the utility modules and integration tests via the RPC client.

### Running

```bash
python3 -m pytest tests/
```

The RPC tests (`test_rpc_client`, `test_rpc`) require the server to be running beforehand:

```bash
python3 src/rpc_server.py
```

### Unit Tests

| Test | What it covers |
|---|---|
| `test_is_prime` | Primality checks including edge cases (1, 2, 3, composites) |
| `test_next_previous_prime` | Forward and backward prime search, including `None` return |
| `test_find_next_twin_primes` | Twin prime pairs after given values |
| `test_is_mersenne_prime` | Mersenne prime detection and rejection of non-Mersenne composites |
| `test_prime_factors` | Factorization of composites, primes, and 1 |
| `test_find_max_prime_timed` | Both sequential and parallel prime search with a random timeout |
| `test_generate_keys_and_encrypt_decrypt` | Full RSA round-trip: generate, encrypt, decrypt |
| `test_encrypt_invalid_message` | ValueError raised for out-of-range messages |
| `test_crack_key` | Private key recovery from a 32-bit public key within timeout |

### Integration Tests

`test_rpc_client` runs the same logic as the unit tests but via the RPC client — all calls go through the socket, serialization, and server dispatch. `test_rpc` runs this test once alone and then five times concurrently via threads, validating correct behaviour under concurrent client load.