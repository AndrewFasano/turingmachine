from typing import Any
import z3
'''
A symbolic execution engine for the game Turing Machine.

The game begins with a set of verifiers configured with some hidden state.
In combination, there is a single solution that will make all verifiers
return True.

A player then makes a guess. Each verifier then checks the guess against their
hidden state and returns a boolean value.

The goal of the game is for the player to find the solution that makes
all verifiers return True in the fewest number of guesses.
'''

NUM_DIGITS = 3

from itertools import product

def generate_selection_flag_combinations(selection_flags):
    # Generate all combinations of selection flags (one from each verifier)
    verifiers = list(selection_flags.keys())
    flag_combinations = product(*(selection_flags[v] for v in verifiers))
    return flag_combinations

class Verifier():
    '''
    Base class for a verifier. 
    '''
    def __init__(self, position1, value1=None, position2=None, value2=None):
        '''
        Store hidden state
        '''
        if position1 is not None and not 0 <= position1 < NUM_DIGITS:
            raise ValueError(f"position1 must be in range [0, {NUM_DIGITS}) but it's {position1}")

        if position2 is not None and not 0 <= position2 < NUM_DIGITS:
            raise ValueError("position2 must be in range [0, {NUM_DIGITS})")

        self.position1 = position1
        self.value1 = value1
        self.position2 = position2
        self.value2 = value2

    def get_public_state(self, extra=None):
        # Return subclass name. Subclass can provide extra info if it wants
        return self.__class__.__name__ + (f"({extra})" if extra else "")

    def __call__(self, guess):
        ''' To be implemented by subclass '''
        if len(guess) != NUM_DIGITS:
            raise ValueError(f"guess must be length {NUM_DIGITS}: but it's {len(guess)}")

        for digit in range(NUM_DIGITS):
            if not (0 < guess[digit] < 6):
                raise ValueError(f"guess[{digit}] must be in range [1, 5]: but it's {guess[digit]}")
            
    def __repr__(self) -> str:
        r = f"{self.__class__.__name__}({self.position1}"
        if self.value1:
            r += f", {self.value1}"
        if self.position2 is not None:
            r += f", {self.position2}"
        if self.value2 is not None:
            r += f", {self.value2}"
        r += ")"
        return r

    def get_possibilities(self, guess):
        raise NotImplementedError("get_possibilities must be implemented by subclass")

    def get_n_possibilities(self, guess):
        # Call subclass to get possibilities, then return length
        return len(self.get_possibilities(guess))

class IsEqualX(Verifier):
    ''' Check if a single entry in guess is equal to a value '''
    ''' Known state: value, but not position'''
    def __call__(self, guess):
        super().__call__(guess)
        return guess[self.position1] == self.value1

    def get_public_state(self):
        return super().get_public_state(self.value1)

    def get_possibilities(self, guess):
        return [x == self.value1 for x in guess]

class DuplicateDigits(Verifier):
    ''' Check if the number of duplicate digits in the guess is equal to a value '''
    ''' Known state: value1 (digit), but not count (value2)'''
    def __call__(self, guess):
        super().__call__(guess)
        # Count the number of times value1 appears in the guess
        return sum([1 for x in guess if x == self.value1]) == self.value2

    def get_public_state(self):
        return super().get_public_state(self.value1)

    def get_possibilities(self, guess):
        # Each result for value2
        results = []
        for target in range(NUM_DIGITS+1):
            # For target number, see if target digit (value1) appears that many times
            results.append(z3.And(*[z3.PbEq([(x == self.value1, 1) for x in guess], target)]))
        return results
    
class IsLessThanX(Verifier):
    ''' Check if a single entry in guess is less than a value '''
    ''' Known state: value, but not position'''
    def __call__(self, guess):
        super().__call__(guess)
        return guess[self.position1] < self.value1

    def get_public_state(self):
        return super().get_public_state(self.value1)
    
    def get_possibilities(self, guess):
        return [x < self.value1 for x in guess]
    
class IsEvenOdd(Verifier):
    ''' Check if a single entry in guess is even or odd. Even if value==0 '''
    ''' Known state: even(vs odd) but not position'''
    def __call__(self, guess):
        super().__call__(guess)
        return guess[self.position1] % 2 == (0 if self.value1 else 1)
    
    def get_public_state(self):
        return super().get_public_state("even" if self.value1 else "odd")

    def get_possibilities(self, guess):
        return [x % 2 == (0 if self.value1 else 1) for x in guess]
    

class IsLessThan(Verifier):
    ''' Check if the digit in position1 is less than the digit in position2 '''
    ''' Neither position is known '''
    def __call__(self, guess):
        super().__call__(guess)
        return guess[self.position1] < guess[self.position2]
    
    def get_possibilities(self, guess):
        # For each digit, it can be greater than any digit that comes after it
        #return [x < y for x in guess for y in guess[guess.index(x)+1:]]
        #return [guess[0] < guess[1], guess[0] < guess[2], guess[1] < guess[2]]
        result = []
        for p1, p2 in zip(range(NUM_DIGITS), range(NUM_DIGITS)):
            if p1 != p2:
                result.append(guess[p1] < guess[p2])
        return result
        

class IsMin(Verifier):
    ''' Check if the digit in position1 is the lowest '''
    def __call__(self, guess):
        super().__call__(guess)
        result = True
        for digit in range(NUM_DIGITS):
            if digit != self.position1:
                result &= guess[self.position1] < guess[digit]
        return result
    
    def get_possibilities(self, guess):
        results = []
        for target in range(NUM_DIGITS):
             # For each target digit, we have a possibility that it's the min
             results.append(z3.And(*[guess[target] < guess[digit] for digit in range(NUM_DIGITS) if digit != target]))
        return results 

class Game():
    def __init__(self):
        self.verifiers = [IsLessThanX(0, 3), IsEvenOdd(0, 1), IsMin(1), IsEqualX(2, 2)]
        #self.verifiers = [IsMin(0), IsEqualX(0, 4), DuplicateDigits(None, 0, None, 2)]
        #self.verifiers = [DuplicateDigits(None, 4, None, 2)] # 2x 4
        #self.verifiers = [IsMin(2), DuplicateDigits(None, 3, None, 2), IsLessThanX(2, 2)]

    def run(self):
        self.report()
        self.results = {}
        for i in range(100):
            print("-"*30)
            concrete_guess, solved = self.guess_loop()

            all_true = False
            if not solved:
                verifier_output = {v: v(concrete_guess) for v in self.verifiers}
                print(f"Guess {i+1}: {concrete_guess} returns")
                all_true = True

                for v, output in verifier_output.items():
                    print(f"\t{v.get_public_state()}: {output}")
                    all_true &= output
                self.results[concrete_guess] = verifier_output

            if solved or all_true:
                print("*"*30)
                print(f"Alleged solution is {concrete_guess} after {i+1} guesses!")
                print("Results:")

                verifier_output = {v: v(concrete_guess) for v in self.verifiers}
                correct = True
                for v, output in verifier_output.items():
                    print(f"\t{v}: {output}")
                    correct &= output

                print("Solution is " + "VALID" if correct else "INVALID")
                print("*"*30)
                return

    def filter_selected_flags(self, selection_flags):
        '''
        We have some prior guesses. Can they tell us about the hidden state of the verifiers?
        '''
        s = z3.Solver()

        # One of the selection flags must be true for each verifier. In our logic
        # this might end up evaluating to NOT 2 being true, but that should be okay?
        # If not we might want PbGt 0 instead of PbEq 1
        for v in self.verifiers:
            s.add(z3.PbEq([(sel, 1) for sel in selection_flags[v]], 1))

        # For each guess in our history, create a new int for that guess, constrained to its actual value
        for guess, results in self.results.items():
            # Old guess is constrained to its actual value
            old_guess = [z3.Int('old_guess' + ("_".join(map(str,guess))) + f'.{x}') for x in range(NUM_DIGITS)]

            # For each digit in the guess, constrain the old guess to be equal to the guess
            for digit in range(len(old_guess)):
                s.add(old_guess[digit] == guess[digit])

            for v in self.verifiers:
                opts = v.get_possibilities(old_guess) # These are the distinct options for this verifier
                result = results[v] # What did this verifier return for this guess?

                # Combine with selection flags to get the actual options we're checking
                actual_opts = [z3.And(sel, opt) for sel, opt in zip(selection_flags[v], opts)]
                #s.add(z3.Or(*actual_opts))

                # The actual_ops expression evaluates to result. Add this to solver
                s.add(z3.Implies(z3.Or(*actual_opts), result)) # XXX is implication correct?

        if s.check() == z3.unsat:
            print(s)
            raise ValueError("No solution found - are multiple guesses valid?")

        # We've now added constraints for all the guesses. Now we can check to identify any impossible
        # selection flags
        impossible = []
        for v in self.verifiers:
            for idx, sel in enumerate(selection_flags[v]):
                s2 = z3.Solver()
                for c in s.assertions():
                    s2.add(c)
                s2.add(sel)

                if s2.check() == z3.unsat:
                    # Adding SEL is unsat so SEL must not be a flag we want
                    # we'll replace 'old_guess_0_3_3.0  with digit3
                    #pretty_name = str(opts[idx]).split(" ")
                    #pretty_name  = ("digit" + pretty_name[0][pretty_name[0].rindex(".")+1:] + " ") + " ".join(pretty_name[1:])
                    #print(f"Given what we've seen verifier {v} cannot be checking condition {idx}: {pretty_name}")
                    print(f"Given what we've seen verifier {v} cannot be checking condition {idx}:\n\t{opts[idx]}")
                    impossible.append((v, sel))

        # Return a list of selection flags that are impossible
        return impossible

    def guess_loop(self):

        # Create our solver for this guess attempt
        s = z3.Solver()

        # Create symbolic guess values for each digit
        guess = [z3.Int(f'guess{x}') for x in range(NUM_DIGITS)]

        # Constrain each digit to be in range [1, 5]
        for digit in guess:
            s.add(digit >= 1, digit <= 5)

        # For each verifier, create a list of selection flags and store that at least one must be true
        selection_flags = {} # verifier -> [selection flags]
        selection_possibilities = {} # verifier -> Count of selection flags
        for v in self.verifiers:
            selection_flags[v] = [z3.Bool(f'selected_{v}_{i}') for i in range(v.get_n_possibilities(guess))]

            # One must be true
            s.add(z3.PbEq([(sel, 1) for sel in selection_flags[v]], 1))

            # Get all possible outputs for this verifier, set selection flag to imply each output
            possibilities = v.get_possibilities(guess)
            selection_possibilities[v] = len(possibilities)
            for idx, (sel, opt) in enumerate(zip(selection_flags[v], possibilities)):
                s.add(z3.Implies(sel, opt))

        # Generate combinations
        flag_combinations = generate_selection_flag_combinations(selection_flags)

        # Now iterate over these combinations and test each one
        for combination in flag_combinations:
            s_test = z3.Solver()
            # Add all existing constraints
            for c in s.assertions():
                s_test.add(c)
            # Add the specific combination of selection flags
            for flag in combination:
                s_test.add(flag)

            if s_test.check() == z3.unsat:
                s.add(z3.Not(z3.And(*[combination])))
                continue

            # Get model, add constraint that we can't use this again
            m = s_test.model()
            first_solution = [m[guess[digit]].as_long() for digit in range(NUM_DIGITS)]
            s_test.add(z3.Or([guess[digit] != first_solution[digit] for digit in range(NUM_DIGITS)]))

            # Check for another solution
            if s_test.check() == z3.sat:
                #print("Multiple solutions found for:", combination)
                s.add(z3.Not(z3.And(*[combination])))

        # With the correct set of selection flags (i.e., one of each), only a single solution would be possible.
        # This doesn't express well in boolean logic. Instead let's enumerate and test

        if len(self.results) > 0:
            # If we had any prior results, filter our selection flags to remove any that we now know are impossible
            for (verifier, impossible_selection) in self.filter_selected_flags(selection_flags):
                s.add(z3.Not(impossible_selection))
                selection_possibilities[verifier] -= 1

        if len(self.results) > 0:
            # Try to enforce that we don't re-try old guesses. BUT if that's not possible, allow it
            s2 = z3.Solver()
            for c in s.assertions():
                s2.add(c)

            for old_guess, details in self.results.items():
                # Add constraint that our guess must not be the same as any previous guess
                s2.add(z3.Not(z3.And(*[old == new for old, new in zip(old_guess, guess)])))

            if s2.check() != z3.unsat:
                s = s2


        if s.check() == z3.unsat:
            print(s)
            raise ValueError("No solution found")

        m = s.model()
        concrete_guess = tuple([m[x].as_long() for x in guess])

        # Did we solve for all verifiers?
        solved = all([selection_possibilities[v] == 1 for v in self.verifiers])

        if not solved:
            for v in self.verifiers:
                #print(f"Verifier {v} has {selection_possibilities[v]} possibilities")
                if selection_possibilities[v] == 1:
                    print(f"Solved for {v}!")

        # Return the guess + results from each verifier
        return (concrete_guess, solved)

    def report(self, show_hidden=True):
        print(f"Public game state: {NUM_DIGITS} digits with {len(self.verifiers)} verifiers:")
        for idx, v in enumerate(self.verifiers):
            print(f"\tVerifier {idx}: {v.get_public_state()}")
        print()

        if show_hidden:
            print("Hidden game state:")
            for idx, v in enumerate(self.verifiers):
                print(f"\tVerifier {idx}: {v}")
            print()


if __name__ == '__main__':
    Game().run()
