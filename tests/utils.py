import random
import string


def generate_random_string(length: int) -> str:
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))  # noqa: S311
