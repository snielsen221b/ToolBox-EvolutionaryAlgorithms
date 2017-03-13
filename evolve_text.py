"""
Evolutionary algorithm, attempts to evolve a given message string.

Uses the DEAP (Distributed Evolutionary Algorithms in Python) framework,
http://deap.readthedocs.org

Usage:
    python evolve_text.py [goal_message]

Full instructions are at:
https://sites.google.com/site/sd15spring/home/project-toolbox/evolutionary-algorithms
"""

import random
import string
import doctest

import numpy    # Used for statistics
from numpy import zeros
from deap import algorithms, base, tools

# -----------------------------------------------------------------------------
#  Global variables
# -----------------------------------------------------------------------------

# Allowable characters include all uppercase letters and space
# You can change these, just be consistent (e.g. in mutate operator)
VALID_CHARS = string.ascii_uppercase + " "

# Control whether all Messages are printed as they are evaluated
VERBOSE = True


# -----------------------------------------------------------------------------
# Message object to use in evolutionary algorithm
# -----------------------------------------------------------------------------

class FitnessMinimizeSingle(base.Fitness):
    """
    Class representing the fitness of a given individual, with a single
    objective that we want to minimize (weight = -1)
    """
    weights = (-1.0, )


class Message(list):
    """
    Representation of an individual Message within the population to be evolved

    We represent the Message as a list of characters (mutable) so it can
    be more easily manipulated by the genetic operators.
    """
    def __init__(self, starting_string=None, min_length=4, max_length=30):
        """
        Create a new Message individual.

        If starting_string is given, initialize the Message with the
        provided string message. Otherwise, initialize to a random string
        message with length between min_length and max_length.
        """
        # Want to minimize a single objective: distance from the goal message
        self.fitness = FitnessMinimizeSingle()

        # Populate Message using starting_string, if given
        if starting_string:
            self.extend(list(starting_string))

        # Otherwise, select an initial length between min and max
        # and populate Message with that many random characters
        else:
            initial_length = random.randint(min_length, max_length)
            for i in range(initial_length):
                self.append(random.choice(VALID_CHARS))

    def __repr__(self):
        """Return a string representation of the Message"""
        # Note: __repr__ (if it exists) is called by __str__. It should provide
        #       the most unambiguous representation of the object possible, and
        #       ideally eval(repr(obj)) == obj
        # See also: http://stackoverflow.com/questions/1436703
        template = '{cls}({val!r})'
        return template.format(cls=self.__class__.__name__,     # "Message"
                               val=self.get_text())

    def get_text(self):
        """Return Message as string (rather than actual list of characters)"""
        return "".join(self)


# -----------------------------------------------------------------------------
# Genetic operators
# -----------------------------------------------------------------------------
memo = {}


def levenshtein_distance(string_1, len_1, string_2, len_2):
    '''finds the Levenshtein distance between string 1
    and string 2
    >>> levenshtein_distance('hello', 5, 'hello', 5)
    0
    >>> levenshtein_distance('catch', 5, 'match', 5)
    1
    >>> levenshtein_distance('catch-22', 8, 'match', 5)
    4
    '''

    # base-case: empty strings
    if len_1 == 0:
        return len_2
    if len_2 == 0:
        return len_1

    # text if last chrarters of strings match
    if string_1[len_1 - 1] == string_2[len_2 - 1]:
        dist = 0
    else:
        dist = 1

    # recurse: return minimum of LD removing char from string_1,
    # removing character from string_2, and deleting char from both
    reduce_1 = levenshtein_distance(string_1, len_1 - 1, string_2, len_2) + 1
    reduce_2 = levenshtein_distance(string_1, len_1, string_2, len_2 - 1) + 1
    reduce_both = levenshtein_distance(string_1, len_1 - 1, string_2, len_2 - 1) + dist
    minimum = min(reduce_1, reduce_2, reduce_both)
    return minimum


def edit_distance(string_1, string_2):
    '''finds the Levnshtein distance using the Warner-Fisher algorithm
    >>> edit_distance('hello', 'hello')
    0
    >>> edit_distance('catch', 'match')
    1
    >>> edit_distance('catch-22', 'match')
    4
    >>> edit_distance('kitten', 'sitting')
    3
    '''
    len_1 = len(string_1)
    len_2 = len(string_2)
    # distance matrix as matrix of zeros len(string_1) by len(string_2)
    d = zeros((len_1, len_2))

    # makes first row of d distance from string_1[i] to empty string
    for i in range(1, len_1):
        d[i, 0] = i

    # makes first column of d distance from string_2[i] to empty string
    for j in range(1, len_2):
        d[0, j] = j

    # iterates through matrix to find levenshtein_distance
    for j in range(1, len_2):
        for i in range(1, len_1):
            # if string_1[i] and string_2[j] are the same, no operation
            # is required
            if string_1[i-1] == string_2[j-1]:
                d[i, j] = d[i-1, j-1]
            else:
                deletion = d[i-1, j] + 1
                insertion = d[i, j-1] + 1
                substitution = d[i-1, j-1] + 1
                d[i, j] = min(deletion, insertion, substitution)
    return int(d[len_1-1, len_2-1])


def evaluate_text(message, goal_text, verbose=VERBOSE):
    """
    Given a Message and a goal_text string, return the Levenshtein distance
    between the Message and the goal_text as a length 1 tuple.
    If verbose is True, print each Message as it is evaluated.
    """
    # distance = levenshtein_distance(message.get_text(), len(message.get_text()),
    #                                 goal_text, len(goal_text))
    distance = edit_distance(message.get_text(), goal_text)
    if verbose:
        print("{msg!s}\t[Distance: {dst!s}]".format(msg=message, dst=distance))
    return (distance, )     # Length 1 tuple, required by DEAP


def mutate_text(message, prob_ins=0.05, prob_del=0.05, prob_sub=0.05):
    """
    Given a Message and independent probabilities for each mutation type,
    return a length 1 tuple containing the mutated Message.

    Possible mutations are:
        Insertion:      Insert a random (legal) character somewhere into
                        the Message
        Deletion:       Delete one of the characters from the Message
        Substitution:   Replace one character of the Message with a random
                        (legal) character
    """
    # Insertion-type mutation
    if random.random() < prob_ins:
        i = random.randint(0, len(message)-1)
        char = random.choice(string.ascii_uppercase + " ")
        message.insert(i, char)
    # Deletion-type mutation
    if random.random() < prob_del:
        i = random.randint(0, len(message)-1)
        message.pop(i)
    # Substitution-type mutation
    if random.random() < prob_sub:
        i = random.randint(0, len(message)-1)
        char = random.choice(string.ascii_uppercase + " ")
        message[i] = char

    return (message, )   # Length 1 tuple, required by DEAP


# -----------------------------------------------------------------------------
# DEAP Toolbox and Algorithm setup
# -----------------------------------------------------------------------------

def get_toolbox(text):
    """Return DEAP Toolbox configured to evolve given 'text' string"""

    # The DEAP Toolbox allows you to register aliases for functions,
    # which can then be called as "toolbox.function"
    toolbox = base.Toolbox()

    # Creating population to be evolved
    toolbox.register("individual", Message)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Genetic operators
    toolbox.register("evaluate", evaluate_text, goal_text=text)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", mutate_text)
    toolbox.register("select", tools.selTournament, tournsize=3)

    # NOTE: You can also pass function arguments as you define aliases, e.g.
    #   toolbox.register("individual", Message, max_length=200)
    #   toolbox.register("mutate", mutate_text, prob_sub=0.18)

    return toolbox


def evolve_string(text):
    """Use evolutionary algorithm (EA) to evolve 'text' string"""

    # Set random number generator initial seed so that results are repeatable.
    # See: https://docs.python.org/2/library/random.html#random.seed
    #      and http://xkcd.com/221
    random.seed(4)

    # Get configured toolbox and create a population of random Messages
    toolbox = get_toolbox(text)
    pop = toolbox.population(n=300)

    # Collect statistics as the EA runs
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean)
    stats.register("std", numpy.std)
    stats.register("min", numpy.min)
    stats.register("max", numpy.max)

    # Run simple EA
    # (See: http://deap.gel.ulaval.ca/doc/dev/api/algo.html for details)
    pop, log = algorithms.eaSimple(pop,
                                   toolbox,
                                   cxpb=0.5,    # Prob. of crossover (mating)
                                   mutpb=0.2,   # Probability of mutation
                                   ngen=500,    # Num. of generations to run
                                   stats=stats)

    return pop, log


# -----------------------------------------------------------------------------
# Run if called from the command line
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    doctest.testmod()

    # Get goal message from command line (optional)
    import sys
    if len(sys.argv) == 1:
        # Default goal of the evolutionary algorithm if not specified.
        # Pretty much the opposite of http://xkcd.com/534
        goal = "SKYNET IS NOW ONLINE"
    else:
        goal = " ".join(sys.argv[1:])

    # Verify that specified goal contains only known valid characters
    # (otherwise we'll never be able to evolve that string)
    for char in goal:
        if char not in VALID_CHARS:
            msg = "Given text {goal!r} contains illegal character {char!r}.\n"
            msg += "Valid set: {val!r}\n"
            raise ValueError(msg.format(goal=goal, char=char, val=VALID_CHARS))

    # Run evolutionary algorithm
    pop, log = evolve_string(goal)
