import random
import string

def gen_pass(length = 20):
    if length < 1:
        raise ValueError("Password length must be at least 1.")
    
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

def flip_coin_f():
    return random.choice(["Heads", "Tails"])

def gen_emojis():
    emojis = [
        "😀", "😂", "😍", "😎", "😢", "😡", "🥳", "🤔", "😱", "👍", "👎", "🎉", "💔", "✨", "🌈"
    ]
    return random.choice(emojis)
