"""Reader and evaluator for the benchmark instances of the knapsack problem with forfeits (KPF).

Instance format (readme.txt of the benchmark, Capobianco et al., 2022): line 1 holds the number of items n, the
number of forfeit pairs l and the capacity b; line 2 holds the profits and line 3 the weights of items 0, ..., n-1;
each forfeit pair k then takes two lines, "1 d_k 2" with its forfeit cost d_k, and "i_k j_k" with its two items.

The objective charges every listed pair, as the integer programming model of the problem does with one variable per
listed pair, so a pair of items listed twice is charged twice:

    f(S) = sum_{i in S} p_i - sum_{k : i_k in S and j_k in S} d_k,    subject to    sum_{i in S} w_i <= b.

Only the Python standard library is used.
"""
import csv
import hashlib
from pathlib import Path


class Instance:
    """A KPF instance: profits, weights, capacity and the list of forfeit pairs (i_k, j_k, d_k)."""

    def __init__(self, name, profits, weights, capacity, pairs):
        self.name = name
        self.profits = profits
        self.weights = weights
        self.capacity = capacity
        self.pairs = pairs
        self.n = len(profits)
        self.l = len(pairs)

    @classmethod
    def read(cls, path, name=None):
        tokens = Path(path).read_text().split()
        pos = 0

        def take(k):
            nonlocal pos
            if pos + k > len(tokens):
                raise ValueError(f"{path}: the file ends before the last forfeit pair")
            out = [int(t) for t in tokens[pos:pos + k]]
            pos += k
            return out

        n, l, capacity = take(3)
        profits = take(n)
        weights = take(n)
        pairs = []
        for k in range(l):
            allowed, cost, size = take(3)
            if allowed != 1 or size != 2:
                raise ValueError(f"{path}: forfeit pair {k} has header {allowed} {cost} {size}, expected 1 d 2")
            i, j = take(2)
            if not (0 <= i < n and 0 <= j < n) or i == j:
                raise ValueError(f"{path}: forfeit pair {k} has items {i} and {j}")
            pairs.append((i, j, cost))
        if pos != len(tokens):
            raise ValueError(f"{path}: {len(tokens) - pos} values after the last forfeit pair")
        return cls(name or instance_name(path), profits, weights, capacity, pairs)

    def evaluate(self, items):
        """Objective value and weight of the solution whose selected items (0-based) are given.

        Raises ValueError when an index is out of range or appears twice."""
        chosen = bytearray(self.n)
        for i in items:
            if not 0 <= i < self.n:
                raise ValueError(f"item {i} is outside 0..{self.n - 1}")
            if chosen[i]:
                raise ValueError(f"item {i} is listed twice")
            chosen[i] = 1
        value = sum(self.profits[i] for i in items)
        weight = sum(self.weights[i] for i in items)
        value -= sum(d for i, j, d in self.pairs if chosen[i] and chosen[j])
        return value, weight


def instance_name(path):
    """'.../LK/1000/01_id_116b_objs_1000_....txt' -> 'LK_1000_01'."""
    path = Path(path)
    return f"{path.parent.parent.name}_{path.parent.name}_{path.name.split('_')[0]}"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def read_manifest(path):
    """data/instances_manifest.csv as a dict: instance name -> row (file, sha256, n, pairs, capacity)."""
    return {row["instance"]: row for row in read_csv(path)}


def parse_items(text):
    """'3 17 42' -> [3, 17, 42]."""
    return [int(t) for t in text.split()]
