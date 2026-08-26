def move_towards(current: float, target: float, dx: float):
    if current < target:
        return min(current + dx, target)
    return max(target, current - dx)
