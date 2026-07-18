# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
"""Polymarket agent environment — what the agent sees each turn."""
from __future__ import annotations

from typing import cast

from wonderwall.simulations.base import BaseEnvironment
from wonderwall.simulations.polymarket.actions import PolymarketAction


class PolymarketEnvironment(BaseEnvironment):
    """Converts Polymarket state into the text prompt the agent observes."""

    async def to_text_prompt(self) -> str:
        action = cast(PolymarketAction, self.action)
        portfolio = await action.view_portfolio()
        markets = await action.browse_markets()

        parts = []

        if portfolio.get("success"):
            balance = portfolio['balance']
            parts.append(f"YOUR PORTFOLIO:\n  Cash: ${balance:.2f}")

            positions = portfolio.get("positions", [])
            if positions:
                total_value = 0
                parts.append("  Open positions:")
                for pos in positions:
                    cost_basis = pos['cost_basis']
                    current_value = pos['current_value']
                    pnl = current_value - cost_basis
                    total_value += current_value

                    parts.append(
                        f"    - Market #{pos['market_id']}: "
                        f"\"{pos['question']}\" — "
                        f"{pos['shares']:.1f} {pos['outcome']} shares "
                        f"@ ${pos['current_price']:.3f} "
                        f"(value: ${current_value:.2f}, "
                        f"P&L: {'+'if pnl>=0 else ''}{pnl:.2f})"
                    )

                portfolio_value = balance + total_value
                parts.append(f"  Total portfolio value: ${portfolio_value:.2f}")
            else:
                parts.append("  No open positions.")

        if markets.get("success") and markets.get("markets"):
            parts.append("\nACTIVE MARKETS:")
            for m in markets["markets"]:
                price_keys = [k for k in m if k.startswith("price_")]
                price_str = ", ".join(
                    f"{k.replace('price_', '')}: ${m[k]:.3f}"
                    for k in price_keys
                )
                num_trades = m.get('num_trades', 0)

                parts.append(
                    f"  #{m['market_id']}: \"{m['question']}\" "
                    f"[{price_str}] "
                    f"({num_trades} trades)"
                )
        else:
            parts.append("\nNo active markets yet.")

        # Inject cross-platform social media context directly into observation
        if self.extra_observation_context:
            parts.append(f"\nSOCIAL MEDIA CONTEXT:\n{self.extra_observation_context}")

        parts.append("\nChoose one available action from the observed facts.")

        return "\n".join(parts)
