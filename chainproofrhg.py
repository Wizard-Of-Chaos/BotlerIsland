"""
Chain-Proof Random Hit Generator module. Contains the ChainProofRHG class and methods.
"""
from math import ceil, log10
from random import random
from functools import partialmethod

from numbers import Number
import operator

EPSILON = 1e-6


def base_to_mean(base_proc):
    """Calculate the effective probability from a given base hit chance."""
    if not (0 <= base_proc <= 1):
        raise ValueError('Probability values lie between 0 and 1 inclusive.')
    elif base_proc >= 0.5:
        return 1 / (2 - base_proc)
    hit_chance = base_proc
    chance_sum = base_proc
    hits_count = base_proc
    # Sum the individual pass chances to get the cumulative number of chances.
    for i in range(2, int(ceil(1 / base_proc)) + 1):
        hit_chance = min(1, base_proc * i) * (1 - chance_sum)
        chance_sum += hit_chance
        hits_count += hit_chance * i
    # Take the reciprocal to convert from 1 in N times happening to a probability.
    return 1 / hits_count


def mean_to_base(mean_proc, epsilon=EPSILON):
    """Uses the bisection method to find the base chance and return it."""
    if not (0 <= mean_proc <= 1):
        raise ValueError('Probability values lie between 0 and 1 inclusive.')
    elif mean_proc >= 2/3:
        return 2 - (1 / mean_proc)
    lower = 0
    upper = mean_proc
    while True:
        # Get the midpoint.
        midpoint = (lower + upper) / 2
        midvalue = base_to_mean(midpoint)
        if abs(midvalue - mean_proc) < epsilon:
            # Return if the error is sufficiently small.
            break
        # Replace the point such that the two points still bracket the true value.
        elif midvalue < mean_proc:
            lower = midpoint
        else:
            upper = midpoint
    return midpoint


class ChainProofRHG(object):
    """Chain-Proof Random Hit Generator for more consistent RNG.

    ChainProofRHG() objects exist as a tool to emulate the style of random hit generation used in
    Warcraft 3, and subsequently, DOTA 2.

    Documentation incomplete.
    """
    __slots__ = (
        '_epsilon', '_fail_count', '_last_count',
        '_lock', '_mean_proc', '_base_proc', '_procnow',
        )

    def __init__(self, mean_proc, epsilon=EPSILON):
        if epsilon > 1e-4:
            raise ValueError('Expected epsilon value too large')
        self._epsilon = epsilon # Minimum accuracy of iteration.
        self._fail_count = 0 # Number of missed hits so far.
        self._last_count = 0 # The number of times needed to hit the last time.
        self._lock = False  # Used to lock __next__ into returning StopIteration.
        self._mean_proc = round(mean_proc, self.round_places) # Initialize the average probability value.
        self._base_proc = mean_to_base(mean_proc, epsilon) # Initialize the base probability value.
        self._procnow = self._base_proc

    def __getattr__(self, name):
        if name in ('p', 'mean_proc'):
            # The average probability for a test to hit.
            return self._mean_proc
        elif name in ('c', 'base_proc'):
            # The base probability of each test.
            return self._base_proc
        elif name == 'procnow':
            # The probability of the next test to hit.
            return self._procnow
        elif name == 'epsilon':
            # The error used when determining self.base_proc
            return self._epsilon
        elif name == 'round_places':
            # Number of accurate digits past the decimal point + 1.
            return -int(ceil(log10(self._epsilon)))
        elif name == 'last_count':
            # The number of times it took to hit the last time.
            return self._last_count
        elif name == 'max_fails':
            # The maximum number of times it can fail in a row.
            return int(ceil(1 / self._base_proc))
        raise AttributeError

    def base_to_mean(self):
        """Calculate the effective probability from the current hit chance for comparison purposes."""
        return base_to_mean(self._base_proc)

    def reset(self):
        """Reset iteration values."""
        self._fail_count = 0
        self._lock = False

    def test_nhits(self, n):
        """Evaluate n hits."""
        return (bool(self) for _ in range(n))

    def __repr__(self):
        """Nicely-formatted expression that can be used in eval()."""
        return '{}({}, {!r})'.format(
            self.__class__.__name__,
            self._mean_proc, self._epsilon,
            )

    # Note: The rich comparison methods take the minimum allowable error into account
    # when comparing against another ChainProofRHG object.
    def _cmp_op(self, other, op):
        """Allow for direct comparison of the probability value as a number."""
        if isinstance(other, ChainProofRHG):
            return op(
                (self._mean_proc, self.round_places),
                (other._mean_proc, other.round_places)
                )
        elif isinstance(other, Number):
            return op(self._mean_proc, other)
        return NotImplemented

    __eq__ = partialmethod(_cmp_op, op=operator.eq)
    __ne__ = partialmethod(_cmp_op, op=operator.ne)
    __lt__ = partialmethod(_cmp_op, op=operator.lt)
    __le__ = partialmethod(_cmp_op, op=operator.le)
    __gt__ = partialmethod(_cmp_op, op=operator.gt)
    __ge__ = partialmethod(_cmp_op, op=operator.ge)

    def __hash__(self):
        """Make the object hashable."""
        return hash((self._mean_proc, self._epsilon))

    def __bool__(self):
        """Evaluate the next hit, returning True if it does, and False otherwise."""
        hit = random() < self._procnow
        if hit:
            self._last_count = self._fail_count + 1
            self._fail_count = 0
        else:
            # If the hit fails, increase the probability for the next hit.
            self._fail_count += 1
        return hit

    def __int__(self):
        """Evaluate the next hit as an integer."""
        return int(bool(self))

    def __float__(self):
        """Returns the probability value."""
        return self._mean_proc

    def __iter__(self):
        """Allows the probability to be used as an iterator, iterating until a hit."""
        self._lock = False
        return self

    def __next__(self):
        """Attempt to roll for a hit until one happens, then raise StopIteration."""
        if self._lock:
            raise StopIteration
        hit = random() < self._procnow
        if hit:
            self._last_count = self._fail_count + 1
            self._fail_count = 0
            self._procnow = self._base_proc
            self._lock = True
            raise StopIteration
        self._procnow = min(1.0, self._procnow + self._base_proc)
        self._fail_count += 1
        return self._fail_count

    def _math_op(self, other, op):
        """Generic mathematical operator function."""
        # Allows usage of common arithmetic operators on ChainProofRHG objects directly for convenience.
        if isinstance(other, ChainProofRHG):
            return self.__class__(
                op(self._mean_proc, other._mean_proc),
                max(self._epsilon, other._epsilon),
                )
        elif isinstance(other, Number):
            return self.__class__(op(self._mean_proc, other), self._epsilon)
        return NotImplemented

    def _rev_math_op(self, other, op):
        """Allows for operations the other way to work."""
        if isinstance(other, Number):
            return self.__class__(op(other, self._mean_proc), self._epsilon)
        return NotImplemented

    # Addition
    __add__ = partialmethod(_math_op, op=operator.add)
    __radd__ = partialmethod(_rev_math_op, op=operator.add)
    # Subtraction
    __sub__ = partialmethod(_math_op, op=operator.sub)
    __rsub__ = partialmethod(_rev_math_op, op=operator.sub)
    # Multiplication
    __mul__ = partialmethod(_math_op, op=operator.mul)
    __rmul__ = partialmethod(_rev_math_op, op=operator.mul)
    # True Division
    __truediv__ = partialmethod(_math_op, op=operator.truediv)
    __rtruediv__ = partialmethod(_rev_math_op, op=operator.truediv)
    # Exponentiation
    __pow__ = partialmethod(_math_op, op=operator.pow)
    __rpow__ = partialmethod(_rev_math_op, op=operator.pow)

    def _logic_op(self, other, op):
        """Returns a ChainProofRHG object using the operator as a probability set logic operator."""
        if isinstance(other, ChainProofRHG):
            return self.__class__(
                op(self._mean_proc, other._mean_proc),
                max(self._epsilon, other._epsilon),
                )
        elif isinstance(other, Number) and 0 <= other <= 1:
            return self.__class__(op(self._mean_proc, other), self._epsilon)
        else:
            raise TypeError("Incompatible operand type between probability and non-probability")

    # P(A) & P(B) = P(A) * P(B)
    __and__ = partialmethod(_logic_op, op=operator.mul)
    __rand__ = partialmethod(_logic_op, op=operator.mul)
    # P(A) ^ P(B) = P(A) + P(B) - 2 * P(A) * P(B)
    __xor__ = partialmethod(_logic_op, op=lambda l, r: l + r - 2*l*r)
    __rxor__ = partialmethod(_logic_op, op=lambda l, r: l + r - 2*l*r)
    # P(A) | P(B) = P(A) + P(B) - P(A) * P(B)
    __or__ = partialmethod(_logic_op, op=lambda l, r: l + r - l*r)
    __ror__ = partialmethod(_logic_op, op=lambda l, r: l + r - l*r)

    # ~P(A) = 1 - P(A)
    def __invert__(self):
        """Return a ChainProofRHG object with the probability that this will not hit."""
        return self.__class__(1 - self._mean_proc)

    def __round__(self, n=0):
        """Allows the use of round() to truncate probability value."""
        return round(self._mean_proc, min(n, self.round_places))


if __name__ == '__main__':
    # Some simple tests.
    cprhg = ChainProofRHG(0.25)
    assert cprhg != ChainProofRHG(0.25, 1e-5)
    print(cprhg)
    assert cprhg == 0.25
    assert abs(cprhg.base_to_mean() - 0.25) < cprhg.epsilon
    print(cprhg.base_to_mean() - 0.25)
    cprhg = ChainProofRHG(0.17)
    print(cprhg)
    assert cprhg.mean_proc == 0.17
    assert cprhg.procnow == cprhg.base_proc
    print(cprhg.procnow)
    print(' '.join(str(i) for i in cprhg), '|', cprhg.last_count)
    a = ChainProofRHG(0.1)
    assert a == 0.1 == ChainProofRHG(0.1)
    assert 0 < a < 1
    assert 0.1 <= a <= 0.1
    b = ChainProofRHG(0.15)
    print(a + b)
    print((a + b).base_proc)
    assert a + b == 0.25
    assert a + 0.1 == 0.2
    assert 0.1 + a == 0.2
    print(0.1 + a)
    a = a + 0.1
    assert a == ChainProofRHG(0.2)
    assert round(a - b, 2) == 0.05
    assert round(a - 0.05, 2) == 0.15
    assert round(0.05 - float(a), 2) == -0.15
    assert a * 5 == 1.
    assert 5 * a == 1.
    assert a * b == 0.03
    b = a * b
    assert b == ChainProofRHG(0.03)
    b = b / a
    assert b == 0.15
    print(a | b)
    print((a | b).base_proc)
    assert a | b == a + b - (a * b)
    print(a & b)
    print((a & b).base_proc)
    assert a & b == a * b
    print(a ^ b)
    print((a ^ b).base_proc)
    assert a ^ b == a + b - (2 * a * b)
    print(~a)
    print((~a).base_proc)
    assert ~~a == a
    cprhg = ChainProofRHG(0.15)
    print(cprhg)
    hitlist = [len([i for i in cprhg]) + 1 for _ in range(25)]
    print(hitlist)
    print(len(hitlist) / sum(hitlist))
    for prob in range(5, 51, 5):
        print(f'{prob:02}%: {mean_to_base(prob/100):0.6f}')
