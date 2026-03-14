import random

subjects = [
    "the quick fox",
    "a tired student",
    "the curious robot",
    "an old scientist",
]

verbs = [
    "jumps over",
    "studies",
    "carefully examines",
    "quietly watches",
]

objects = [
    "the glowing computer",
    "a mysterious signal",
    "the strange machine",
    "a complicated puzzle",
]

endings = [
    "late at night",
    "during the experiment",
    "while everyone is sleeping",
    "without making a sound",
]


def generate_sentence():
    sentence = (
        random.choice(subjects) + " " +
        random.choice(verbs) + " " +
        random.choice(objects) + " " +
        random.choice(endings)
    )

    return sentence.capitalize() + "."