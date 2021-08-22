def draw_box(usage, active, inactive):
    usage = int(usage)
    if usage < 20:
        return f"{active}{inactive * 9}"
    elif usage == 100:
        return active * 10

    activec = usage // 10
    black = 10 - activec
    return f"{active * activec}{inactive * black}"