#!/usr/bin/env python
"""
DeskAgent CLI Runner.
Provides a simple command line interface to chat with the PlannerAgent directly.
"""

from __future__ import annotations

import sys
from pathlib import Path
import asyncio

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.agents.planner_agent import PlannerAgent
from backend.core.logger import get_logger

logger = get_logger("ai-companion.cli")

async def chat_loop():
    print("====================================================")
    print("         DeskAgent Command Line Interface           ")
    print("====================================================")
    print("Loading PlannerAgent...")
    
    # Initialize agents
    planner = PlannerAgent()
    
    print("Agent is ready! Type 'exit' or 'quit' to end.")
    print("====================================================")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break
                
            print("DeskAgent is thinking...")
            
            # Send message to planner
            response = await planner.handle_message(user_input, context={})
            
            # Print response
            print(f"\nDeskAgent: {response.get('text', 'No response text.')}")
            if "emotion" in response:
                print(f"Emotion: [{response.get('emotion')}]")
            if "motion" in response:
                print(f"Motion: [{response.get('motion')}]")
                
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error during interaction: {e}", exc_info=True)
            print(f"\nSystem Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        pass
