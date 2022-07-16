def formatColor(text, color: str = "reset"):
    grey = "\033[;90m"
    gray = "\033[;90m"
    yellow = "\033[;33m"
    red = "\033[1;31m"
    green = "\033[;32m"
    reset = "\033[0;m"

    if color == "bold_red":
        return "\033[;31m" + str(text) + reset
    elif color == "gray":
        return gray + str(text) + reset
    elif color == "green":
        return green + str(text) + reset
    elif color == "grey":
        return grey + str(text) + reset
    elif color == "red":
        return red + str(text) + reset
    elif color == "reset":
        return reset + str(text) + reset
    elif color == "yellow":
        return yellow + str(text) + reset
    else:
        return "Invalid Color: Please use either:\n• grey/gray\n• yellow\n• red\n• bold_red\n• green\n• reset (resets color back to white)"
