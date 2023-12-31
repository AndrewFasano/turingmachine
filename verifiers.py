import z3

# These are the verifier cards used in the actual game with
# their numerical IDs and descriptions.


class Verifier():
    '''
    Base class for a verifier. 
    '''
    def __init__(self, num_digits, position1, value1=None, position2=None, value2=None):
        '''
        Store hidden state
        '''
        self.num_digits = num_digits
        if position1 is not None and not 0 <= position1 < self.num_digits:
            raise ValueError(f"position1 must be in range [0, {self.num_digits}) but it's {position1}")

        if position2 is not None and not 0 <= position2 < self.num_digits:
            raise ValueError("position2 must be in range [0, {self.num_digits})")

        self.position1 = position1
        self.value1 = value1
        self.position2 = position2
        self.value2 = value2

    def get_public_state(self, extra=None):
        # Return subclass name. Subclass can provide extra info if it wants
        return self.__class__.__name__ + (f"({extra})" if extra else "")

    def __call__(self, guess):
        ''' To be implemented by subclass '''
        if len(guess) != self.num_digits:
            raise ValueError(f"guess must be length {self.num_digits}: but it's {len(guess)}")

        for digit in range(self.num_digits):
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
        for target in range(self.num_digits+1):
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
        for p1, p2 in zip(range(self.num_digits), range(self.num_digits)):
            if p1 != p2:
                result.append(guess[p1] < guess[p2])
        return result
        

class IsMin(Verifier):
    ''' Check if the digit in position1 is the lowest '''
    def __call__(self, guess):
        super().__call__(guess)
        result = True
        for digit in range(self.num_digits):
            if digit != self.position1:
                result &= guess[self.position1] < guess[digit]
        return result
    
    def get_possibilities(self, guess):
        results = []
        for target in range(self.num_digits):
             # For each target digit, we have a possibility that it's the min
             results.append(z3.And(*[guess[target] < guess[digit] for digit in range(self.num_digits) if digit != target]))
        return results 


# FOR 3 DIGIT GAMEPLAY: 0=triangle, 1=square, 2=circle
game = {
    1: {"desc": "the △ number compared to 1",
        "model": None},
    2: {"desc": "the △ number compared to 3",
        "model": None},
    3: {"desc": "the □ number compared to 3",
        "model": None},
    4: {"desc": "the □ number compared to 4",
        "model": None},
    5: {"desc": "if △ is even or odd",
        "model": None},
    6: {"desc": "if □ is even or odd",
        "model": None},
    7: {"desc": "if ○ is even or odd",
        "model": None},
    8: {"desc": "the number of 1s in the code",
        "model": None},
    9: {"desc": "the number of 3s in the code",
        "model": None},
    10: {"desc": "the number of 4s in the code",
         "model": None},
    11: {"desc": "the △ number compared to the □ number",
         "model": None},
    12: {"desc": "the △ number compared to the ○ number",
         "model": None},
    13: {"desc": "the □ number compared to the ○ number",
         "model": None},
    14: {"desc": "which colour's number is smaller than either of the others",
         "model": None},
    15: {"desc": "which colour's number is larger than either of the others",
         "model": None},
    16: {"desc": "the number of even numbers compared to the number of odd numbers",
         "model": None},
    17: {"desc": "how many even numbers there are in the code",
         "model": None},
    18: {"desc": "if the sum of all the numbers is even or odd",
         "model": None},
    19: {"desc": "the sum of △ and □ compared to 6",
         "model": None},
    20: {"desc": "if a number repeats itself in the code",
         "model": None},
    21: {"desc": "if there is a number present exactly twice",
         "model": None},
    22: {"desc": "if the 3 numbers in the code are in ascending order, descending order, or no order",
         "model": None},
    23: {"desc": "the sum of all numbers compared to 6",
         "model": None},
    24: {"desc": "if there is a sequence of ascending numbers",
         "model": None},
    25: {"desc": "if there is a sequence of ascending or descending numbers",
         "model": None},
    26: {"desc": "that a specific colour is less than 3",
         "model": None},
    27: {"desc": "that a specific colour is less than 4",
         "model": None},
    28: {"desc": "that a specific colour is equal to 1",
         "model": None},
    29: {"desc": "that a specific colour is equal to 3",
         "model": None},
    30: {"desc": "that a specific colour is equal to 4",
         "model": None},
    31: {"desc": "that a specific colour is greater than 1",
         "model": None},
    32: {"desc": "that a specific colour is greater than 3",
         "model": None},
    33: {"desc": "that a specific colour is even or odd",
         "model": None},
    34: {"desc": "which colour has the smallest number (or is tied for the smallest number)",
         "model": None},
    35: {"desc": "which colour has the largest number (or is tied for the largest number)",
         "model": None},
    36: {"desc": "the sum of all the numbers is a multiple of 3 or 4 or 5",
         "model": None},
    37: {"desc": "the sum of 2 specific colours is equal to 4",
         "model": None},
    38: {"desc": "the sum of 2 specific colours is equal to 6",
         "model": None},
    39: {"desc": "the number of one specific colour compared to 1",
         "model": None},
    40: {"desc": "the number of one specific colour compared to 3",
         "model": None},
    41: {"desc": "the number of one specific colour compared to 4",
         "model": None},
    42: {"desc": "which colour is the smallest or the largest",
         "model": None},

    43: {"desc": "the △ number compared to the number of another specific colour",
         "model": None},
    44: {"desc": "the □ number compared to the number of another specific colour",
         "model": None},
    45: {"desc": "how many 1s OR how many 3s there are in the code",
         "model": None},
    46: {"desc": "how many 3s OR how many 4s there are in the code",
         "model": None},
    47: {"desc": "how many 1s OR how many 4s there are in the code",
         "model": None},
    48: {"desc": "one specific colour compared to another specific colour",
         "model": None},
}
#
#game[1]['model'] = CompareDigitToConstant(digit=0, compared_to_constant=1, private_comparor=None)
#game[2]['model'] = CompareDigitToConstant(digit=0, compared_to_constant=3, private_comparor=None)
#game[3]['model'] = CompareDigitToConstant(digit=1, compared_to_constant=3, private_comparor=None)
game[4]['model'] = CompareDigitToConstant(digit=1, compared_to_constant=4, private_comparor=None)
#game[5]['model'] = IsEvenOddDigit(digit=0, private_even=None)
#game[6]['model'] = IsEvenOddDigit(digit=1, private_even=None)
#game[7]['model'] = IsEvenOddDigit(digit=2, private_even=None)
#game[8]['model'] = CountDigits(count_of=1, private_count=None)
game[9]['model'] = CountDigits(count_of=3, private_count=None)
#game[10]['model'] = CountDigits(count_of=4, private_count=None)
game[11]['model'] = CompareDigitToDigit(digit1=0, digit2=1, private_comparor=None)
#game[12]['model'] = CompareDigitToDigit(digit1=0, digit2=2, private_comparor=None)
#game[13]['model'] = CompareDigitToDigit(digit1=1, digit2=2, private_comparor=None)
game[14]['model'] = WhichIsSmallest(private_digit=None)
#game[15]['model'] = WhichIsLargest(private_digit=None)
#game[16]['model'] = CountEvenVsOdd(private_comparor=None)
#game[17]['model'] = CountEven(private_count=None)
#game[18]['model'] = IsSumEvenOdd(private_even=None)
#game[19]['model'] = CompareDigitSumToConstant(digits=[0, 1], compared_to_constant=6, private_comparor=None)
#game[20]['model'] = DoesAnyDigitRepeat(private_bool=None)
#game[21]['model'] = DoesAnyDigitRepeatTimes(count=2, private_bool=None)
#game[22]['model'] = IsAscendingDescendingNeither(private_order=None)
#game[23]['model'] = CompareSumToConstant(compared_to_constant=6, private_comparor=None)
#game[24]['model'] = DoesAscendingSequenceExist(private_bool=None)
#game[25]['model'] = DoesAscendingOrDescendingSequenceExist(private_bool=None)
#game[26]['model'] = CompareUnknownToConstant(compared_to_constant=3, comparor='<', priviate_digit=None)
#game[27]['model'] = CompareUnknownToConstant(compared_to_constant=4, comparor='<', priviate_digit=None)
#game[28]['model'] = CompareUnknownToConstant(compared_to_constant=1, comparor='=', priviate_digit=None)
#game[29]['model'] = CompareUnknownToConstant(compared_to_constant=3, comparor='=', priviate_digit=None)
#game[30]['model'] = CompareUnknownToConstant(compared_to_constant=4, comparor='=', priviate_digit=None)
#game[31]['model'] = CompareUnknownToConstant(compared_to_constant=1, comparor='>', priviate_digit=None)
#game[32]['model'] = CompareUnknownToConstant(compared_to_constant=3, comparor='>', priviate_digit=None)
#game[33]['model'] = IsEvenOdd(private_digit=None, priviate_even=None)
#game[34]['model'] = WhichIsSmallestOrTied(private_digit=None)
#game[35]['model'] = WhichIsLaregestOrTied(private_digit=None)
#game[36]['model'] = IsSumMultipleOf(private_multiple=None)
#game[37]['model'] = CompareSumOfUnknownsToConstant(compared_to_constant=4, comparor='=' private_digits=None)
#game[38]['model'] = CompareSumOfUnknownsToConstant(compared_to_constant=6, comparor='=' private_digits=None)
#game[39]['model'] = CompareUnknownToConstant(compared_to_constant=1, private_comparor=None, priviate_digit=None)
#game[40]['model'] = CompareUnknownToConstant(compared_to_constant=3, private_comparor=None, priviate_digit=None)
#game[41]['model'] = CompareUnknownToConstant(compared_to_constant=4, private_comparor=None, priviate_digit=None)
#game[42]['model'] = WhichIsSmallestOrLargest(private_digit=None, private_smallest=None)
#game[43]['model'] = CompareDigitToUnknown(digit=0, private_comparor=None, priviate_digit=None)
#game[44]['model'] = CompareDigitToUnknown(digit=1, private_comparor=None, priviate_digit=None)
#game[45]['model'] = CountDigitsOr(count_of=[1, 3], private_count=None, private_target=None)
#game[46]['model'] = CountDigitsOr(count_of=[3, 4], private_count=None, private_target=None)
#game[47]['model'] = CountDigitsOr(count_of=[1, 4], private_count=None, private_target=None)
#game[48]['model'] = CompareUnkownToUnknown(private_comparor=None, priviate_digit1=None, priviate_digit2=None)


def verifiers_from_numbers(numbers):
    ''' Return a list of verifiers from a list of numbers '''
    ''' Example: 4, 9, 11, 14 '''
    return [game[number]['model'] for number in numbers]