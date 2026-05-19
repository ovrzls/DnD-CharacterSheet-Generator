"""
Character creation wizard -- guides player through the 7-step flow.

Step 1: Select race         (from Open5e, filtered by active sources)
Step 2: Select class        (from Open5e, filtered by active sources)
Step 3: Select background   (from Open5e, filtered by active sources)
Step 4: Ability scores      (standard array / point buy / random roll)
Step 5: Choose level        (1-5 for prototype)
Step 6: Equipment           (standard best-fit OR randomized appropriate)
Step 7: Spells              (random OR select from list -- skipped for non-casters)

Target deployment: Apache server (GoDaddy) -> Flask web UI is the end goal.
Desktop tkinter build available for local testing.
"""
# TODO (Milestone 5): implement wizard UI


class CharacterWizard:
    """
    Step-by-step character creation wizard.
    Drives the full 7-step flow and returns a completed Character.
    """

    def __init__(self, source_manager=None):
        raise NotImplementedError("CharacterWizard not yet implemented — Milestone 5 task")

    def run(self):
        """Execute the full wizard flow and return a completed Character."""
        raise NotImplementedError("CharacterWizard.run() not yet implemented")
