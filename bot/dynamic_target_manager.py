"""
🎯 Dynamic Daily Target Manager
Calculates the daily profit target as a percentage of the starting equity,
allowing the target to grow as the bot's capital increases.
"""

from .config import settings
from .util import logger

class DynamicTargetManager:
    def __init__(self):
        if not settings.dynamic_target_enabled:
            self.target_rate = 0
            logger.info("🎯 Dynamic daily target is DISABLED.")
            return

        if settings.initial_target_capital <= 0:
            raise ValueError("initial_target_capital must be positive.")

        # Calculate the target rate based on the initial configuration
        self.target_rate = settings.initial_daily_target_usd / settings.initial_target_capital
        logger.info(f"🎯 Dynamic daily target ENABLED. Target rate: {self.target_rate:.2%}")
        logger.info(f"   (Based on initial target of ${settings.initial_daily_target_usd} for ${settings.initial_target_capital} capital)")

    def get_daily_target(self, daily_start_equity: float) -> float:
        """
        Calculates the current daily profit target.

        Args:
            daily_start_equity: The account equity at the start of the trading day.

        Returns:
            The calculated daily profit target in USD.
        """
        if not settings.dynamic_target_enabled:
            # If disabled, return the fixed initial target
            return settings.initial_daily_target_usd

        # Calculate the dynamic target
        dynamic_target = daily_start_equity * self.target_rate

        # Ensure the target is not below the configured minimum
        final_target = max(dynamic_target, settings.min_daily_target_usd)

        return final_target

# Global instance
dynamic_target_manager = DynamicTargetManager()