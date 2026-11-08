"""Word lists for the game.

Small on purpose: swap in a bigger list (or load one from a file or S3)
once the rest of the pipeline is working.
"""

ANSWERS = [
    "apple", "brain", "chair", "dream", "eagle", "flame", "grape", "house",
    "ivory", "joker", "knife", "lemon", "magic", "night", "ocean", "piano",
    "queen", "river", "stone", "tiger", "ultra", "voice", "water", "xenon",
    "youth", "zebra", "angle", "beach", "cloud", "dance", "earth", "field",
    "ghost", "heart", "image", "jelly", "karma", "light", "money", "noble",
    "olive", "plant", "quiet", "robot", "smile", "train", "unity", "vivid",
    "world", "yield", "alarm", "bread", "candy", "dairy", "event", "frost",
    "glass", "honey", "input", "juice", "kiosk", "laser", "mango", "nurse",
    "orbit", "paper", "quest", "radio", "sugar", "table", "urban", "vapor",
    "wheel", "pixel", "rapid", "swift", "crane", "slate", "trace", "adieu",
]

# Extra words accepted as guesses but never picked as the answer.
EXTRA_VALID = [
    "about", "above", "adult", "after", "again", "agree", "ahead", "allow",
    "alone", "along", "among", "basic", "begin", "black", "board", "brave",
    "break", "bring", "build", "carry", "catch", "cause", "check", "child",
    "clean", "clear", "close", "coach", "count", "cover", "daily", "drink",
    "drive", "early", "empty", "enjoy", "enter", "equal", "every", "faith",
    "first", "floor", "focus", "force", "frame", "fresh", "front", "fruit",
    "given", "grand", "great", "green", "group", "guess", "happy", "heavy",
    "horse", "hotel", "human", "judge", "known", "large", "later", "learn",
    "least", "leave", "level", "local", "lucky", "lunch", "major", "match",
    "maybe", "metal", "might", "minor", "model", "month", "mouth", "movie",
    "music", "never", "newly", "other", "party", "peace", "phone", "place",
    "point", "power", "price", "proud", "quick", "raise", "reach", "ready",
    "right", "round", "scale", "scene", "score", "sense", "shape", "share",
    "sharp", "shift", "short", "since", "sleep", "small", "solid", "sound",
    "space", "speak", "speed", "spend", "sport", "staff", "stage", "start",
    "state", "steam", "still", "story", "study", "style", "sweet", "teach",
    "thank", "their", "there", "thing", "think", "three", "title", "total",
    "touch", "tower", "trade", "treat", "trial", "trust", "truth", "twice",
    "under", "until", "usual", "value", "video", "visit", "waste", "watch",
    "where", "which", "while", "white", "whole", "woman", "worry", "write",
    "wrong", "young",
]

VALID_GUESSES = frozenset(ANSWERS) | frozenset(EXTRA_VALID)
