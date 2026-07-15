from app.utils.solver import PCOptimizationSolver


def apply_objective(solver: PCOptimizationSolver) -> None:
    """Apply the solver's objective function to the CP-SAT model."""
    solver.set_objective()
