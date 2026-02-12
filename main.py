import random
from fastmcp import FastMCP

mcp = FastMCP(name="Demo Server")

@mcp.tool()
def get_random_number(min: int, max: int) -> int:
    """Returns a random number between min and max."""
    return random.randint(min, max)

@mcp.tool()
def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

@mcp.tool()
def roll_dice(n_dice: int = 1) -> list[int]:
    """Rolls a number of dice."""
    return [random.randint(1, 6) for _ in range(n_dice)]

if __name__ == "__main__":
    mcp.run()