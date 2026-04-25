"""
encryption.py

Implementation of various cryptography functions.

Author: Filipe Paredes (filipeparedes3@gmail.com)

"""

import math
import random
import time
from typing import Tuple, Optional
from multiprocessing import Process, Value, cpu_count, Array

try:
    from utils import calculations
except ImportError:
    from src.utils import calculations

def _generate_large_prime(bits: int) -> int:
    while True:
        num = random.getrandbits(bits)
        num |= (1 << bits - 1) | 1  # Garante que tem o bit mais alto e é ímpar
        if calculations.is_prime(num):
            return num


def generate_keys(bits: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Randomly generates a pair of RSA keys, one public and another private"""
    half_bits = bits // 2

    # Gera dois primos diferentes
    p = _generate_large_prime(half_bits)
    q = _generate_large_prime(half_bits)
    while p == q:
        q = _generate_large_prime(half_bits)

    n = p * q
    phi = (p - 1) * (q - 1)

    e = 65537
    # Garante que e é coprimo de "phi"
    while math.gcd(e, phi) != 1:
        e += 2  # Em último caso, sobe para outro primo ímpar

    # Inverso modular
    d = pow(e, -1, phi)

    public_key = (n, e)
    private_key = (n, d)

    return public_key, private_key


def encrypt(message: int, pub_key: Tuple[int, int]) -> int:
    """Encrypts a message with a public key"""
    n, e = pub_key

    # Verifica se a mensagem é válida
    if not 0 < message < n:
        raise ValueError("Message must be between 0 and n.")

    # Encripta com potência modular
    ciphertext = pow(message, e, n)

    return ciphertext


def decrypt(ciphertext: int, priv_key: Tuple[int, int]) -> int:
    """Decrypts a message with a private key"""
    n, d = priv_key
    message = pow(ciphertext, d, n)

    return message


def _try_factors(n: int, start: int, step: int, found_flag, result):
    limit = int(math.isqrt(n)) + 1

    for i in range(start, limit, step):
        if found_flag.value:
            return
        if n % i == 0:
            with found_flag.get_lock():
                if not found_flag.value:
                    result[0] = i
                    result[1] = n // i
                    found_flag.value = True
            return


def crack_key(n: int, e: int, timeout: int = 15) -> Optional[Tuple[int, int]]:
    """Tries to crack a private key from a public key"""
    found_flag = Value('b', False)
    result = Array('Q', [0, 0])  # unsigned long

    processes = []
    for i in range(cpu_count()):
        p = Process(target=_try_factors, args=(n, 2 + i, cpu_count(), found_flag, result))
        p.start()
        processes.append(p)

    start_time = time.time()
    while time.time() - start_time < timeout and not found_flag.value:
        time.sleep(0.1)

    for p in processes:
        p.terminate()
        p.join()

    if found_flag.value:
        p, q = result[0], result[1]
        phi = (p - 1) * (q - 1)
        try:
            d = pow(e, -1, phi)
        except ValueError:
            return None

        # Verificação da validade da chave
        test_message = 42
        encrypted = pow(test_message, e, n)
        decrypted = pow(encrypted, d, n)
        if decrypted == test_message:
            return n, d

    return None
