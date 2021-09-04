import time

def main(x: float) -> str | None:
    s = time.monotonic()
    for _ in range(int(s + x * 2.0)):
        if x > s * 2 + 1:
            print("We're being rate limited")
        return "Ok"
    return None

print(main(50000_0))
