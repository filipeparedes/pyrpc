"""
calculo.py

Implementation of various mathematical functions.

Author: Filipe Paredes
Student Number: 202300257
"""

import math
import time
from typing import Optional, Tuple, List
from multiprocessing import Process, Value, Lock, cpu_count


def is_prime(n: int) -> bool:
    """Checks if n is prime using 6k ± 1 optimization."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    limit = math.isqrt(n)
    i = 5
    while i <= limit:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _worker(start: int, step: int, max_prime: Value, lock: Lock, stop_time: float):
    n = start
    while time.time() < stop_time:
        if n % 3 != 0 and n % 5 != 0 and is_prime(n):
            with lock:
                max_prime.value = max(max_prime.value, n)
        n += step


def find_max_prime_parallel(timeout: int) -> int:
    """Finds the largest prime number using multiple processes, searching for timeout time"""
    max_prime = Value('q', 2)
    lock = Lock()
    stop_time = time.time() + timeout
    processes = []

    num_workers = cpu_count()

    for i in range(num_workers):
        # Cada processo começa num impar diferente (3 + 2i)
        # step = 2 * num_workers para manter apenas impares e evitar sobreposição entre workers
        p = Process(target=_worker, args=(3 + 2 * i, 2 * num_workers, max_prime, lock, stop_time))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    return max_prime.value


def find_max_prime_sequential(timeout: int) -> int:
    """Finds the largest prime number in a sequential manner, searching for timeout time"""
    start_time = time.time()
    # Começa no primeiro número primo
    n = 2
    last_prime = n

    while True:
        # Acaba a procura quando o tempo acabar
        if time.time() - start_time > timeout:
            break
        if is_prime(n):
            last_prime = n
        n += 1

    return last_prime


def find_next_twin_primes(n: int) -> Optional[Tuple[int, int]]:
    """Finds the next twin prime numbers of n"""
    i = n + 1
    while True:
        # Verifica se o próximo par de números são primos gémeos
        if is_prime(i) and is_prime(i + 2):
            return i, i + 2
        i += 1


def is_mersenne_prime(n: int) -> bool:
    """Determines if n is a mersenne prime"""
    if n < 2:
        return False
    # n = 2^p-1 <=>
    p = math.log2(n + 1)

    return p.is_integer() and is_prime(int(p)) and is_prime(n)


def prime_factors(n: int) -> List[int]:
    """Factors n into prime factors, ordered by ascending order"""
    factors = []
    i = 2
    while i * i <= n:
        while n % i == 0:
            factors.append(i)
            n //= i
        i += 1
    if n > 1:
        factors.append(n)

    return factors


def next_prime(n: int) -> int:
    """Finds the next prime number larger than n"""
    i = n + 1
    while True:
        if is_prime(i):
            return i
        i += 1


def previous_prime(n: int) -> Optional[int]:
    """Finds the previous prime number smaller than n"""
    #Contagem decrescente de n-1 a 0
    for i in range(n - 1, 1, -1):
        if is_prime(i):
            return i
    return None


if __name__ == '__main__':
    print(find_max_prime_sequential(1))
    print(find_max_prime_parallel(1))
