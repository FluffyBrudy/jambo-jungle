def section(title: str):
    print(f"\n=== {title} ===")


class C:
    def __new__(cls, *args, **kwargs):
        print(f"C.__new__ got: args={args}, kwargs={kwargs}")
        return super().__new__(cls)

    def __init__(self, x, y, mode="normal", speed=1):
        print(f"C.__init__ got: x={x}, y={y}, mode={mode}, speed={speed}")
        self.x, self.y, self.mode, self.speed = x, y, mode, speed


section("Mixed: C(10, 20, mode='fast', speed=5)")
c = C(10, 20, mode="fast", speed=5)
print(f"result: x={c.x}, y={c.y}, mode={c.mode}, speed={c.speed}")

section("Pure kwargs: C(x=1, y=2, mode='slow')")
c2 = C(x=1, y=2, mode="slow")
print(f"result: x={c2.x}, y={c2.y}, mode={c2.mode}, speed={c2.speed}")


class D:
    def __new__(cls, x, y, mode="normal"):
        print(f"D.__new__ got explicit: x={x}, y={y}, mode={mode}")
        return super().__new__(cls)

    def __init__(self, x, y, mode="normal"):
        self.x, self.y, self.mode = x, y, mode


section("Explicit __new__ signature: D(7, 8, mode='fast')")
d = D(7, 8, mode="fast")
print(f"result: x={d.x}, y={d.y}, mode={d.mode}")
