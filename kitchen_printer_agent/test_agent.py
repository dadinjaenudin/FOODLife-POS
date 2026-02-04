"""Quick test script for agent"""
import sys
import traceback

try:
    print("Importing KitchenAgent...")
    from kitchen_agent import KitchenAgent
    
    print("Creating agent instance...")
    agent = KitchenAgent()
    
    print("Agent created successfully!")
    print(f"Agent name: {agent.agent_name}")
    print(f"Station codes: {agent.station_codes}")
    print(f"Poll interval: {agent.poll_interval}s")
    
    print("\nStarting agent...")
    agent.start()
    
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
