"""Pure re-implementations of the game's Luau formulas.

Nothing in this package reads files, the clock, the environment or global
random state. Every constant arrives as an argument (taken from config.json by
the caller) and every random number comes from an injected function. That
keeps the formulas trivially unit-testable against the golden values, makes
results reproducible, and means a data change can never require a code change
here unless the game's formula itself changed.
"""
