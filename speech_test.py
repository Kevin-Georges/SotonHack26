import asyncio
from sentence_generator import generate_sentence
from speech_to_text import run


def calculate_accuracy(expected, spoken):

    expected_words = expected.lower().replace(".", "").split()
    spoken_words = spoken.lower().replace(".", "").split()

    matches = 0

    for word in expected_words:
        if word in spoken_words:
            matches += 1

    accuracy = matches / len(expected_words)

    return accuracy


async def main():

    sentence = generate_sentence()

    print("\nPlease read the following sentence aloud:\n")
    print(sentence)
    print("\nListening...\n")

    transcript = await run()

    print("\nExpected:")
    print(sentence)

    print("\nDetected:")
    print(transcript)

    accuracy = calculate_accuracy(sentence, transcript)

    print(f"\nAccuracy Score: {accuracy:.2%}")


if __name__ == "__main__":
    asyncio.run(main())