#!/usr/bin/env python3
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from packages.agents.centinela_agents.provider_factory import get_provider
from packages.agents.centinela_agents.agents.analista import explain_cause
from packages.agents.centinela_agents.tools import ToolRegistry

print("=" * 70)
print("TESTING ANALISTA WITH OLLAMA LOCAL")
print("=" * 70)

# Get Ollama provider
provider = get_provider()
print(f"\n[PROVIDER] Using: {provider.config.provider} / {provider.config.model}")

# Create empty tool registry (stub)
tools = ToolRegistry()

# Sample alert
alert = {
    "metric": "monthly_revenue",
    "entity": "ACME Corp",
    "day": "2026-10-03",
    "severity": "high",
    "cause_rejections": [],
}

print(f"\n[ALERT] Processing:")
print(f"  Metric: {alert['metric']}")
print(f"  Entity: {alert['entity']}")
print(f"  Day: {alert['day']}")

print(f"\n[CALLING] Analista...")
result = explain_cause(provider, alert, tools)

print(f"\n[RESPONSE] Cause Analysis:")
if result.get("error"):
    print(f"  Error: {result['error']}")
else:
    cause = result.get("cause", {})
    print(f"  Kind: {cause.get('kind')}")

    if cause.get('kind') == 'identified':
        print(f"  Explanation: {cause.get('sentence')}")
        print(f"  Evidence ({len(cause.get('evidence', []))} items):")
        for i, evidence in enumerate(cause.get('evidence', []), 1):
            print(f"    {i}. {evidence.get('claim')}")
            if evidence.get('figures'):
                for fig in evidence.get('figures', []):
                    print(f"       - Value: {fig.get('value')} (queryId: {fig.get('queryId')})")
    else:
        print(f"  Reason: {cause.get('reason')}")
        queries = cause.get('queriesReviewed', [])
        if queries:
            print(f"  Queries Reviewed: {queries}")

print("\n" + "=" * 70)
print("[DONE] Analista completed with real Ollama response")
print("=" * 70)
