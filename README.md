# GenLayer Appeal Process  Appeal-Aware Verdict System

A practical implementation of the GenLayer Appeal Process built on Testnet Bradbury. The contract demonstrates how Optimistic Democracy handles disputed verdicts through escalating validator rounds.

---

## What is in this repo

appeal_verdict.py is an Intelligent Contract that evaluates cases through AI validators and supports a full appeal cycle. When a verdict is disputed, a new expanded validator set re-evaluates the case considering the appeal reason, which is exactly how the GenLayer Appeal Process works at the protocol level.

## Why I built this

The Appeal Process is one of the most interesting parts of GenLayer but there were no practical examples showing it working inside an Intelligent Contract. I wanted to build something that actually goes through the full cycle from initial evaluation to appeal to final verdict so you can see how the validator set responds to a challenge.

## How it works

Someone submits a case with a title, description, and an evidence URL. The contract fetches the evidence page and an AI judge evaluates it through Optimistic Democracy consensus. If the initial verdict is disputed, anyone can register an appeal with a reason. The contract then runs a re-evaluation where the AI judge considers both the original evidence and the appeal reason before reaching a final verdict.

The appeal can be escalated up to 3 rounds. Each round the validator set in the network expands, doubling until consensus is reached, which mirrors the real GenLayer Appeal Process described in the docs at https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/appeal-process.

## Functions

submit_case takes a title, description, and evidence URL and creates a new case in pending status.

evaluate takes a case id and triggers the AI evaluation through Optimistic Democracy. The verdict is APPROVE or REJECT with a confidence score and reasoning.

register_appeal takes a case id and a reason for the appeal. The reason must be at least 10 characters. The case moves to appealed status.

re_evaluate takes a case id and runs the appeal re-evaluation. The AI judge reads the previous verdict and the appeal reason before deciding whether to uphold or overturn it.

get_case shows the full case state including status, verdict, confidence, appeal round, and reasoning.

## Test results

Submitted a smart contract audit dispute where a developer claimed the client refused to pay after requesting out-of-scope changes. Initial verdict went to APPROVE with 75% confidence. After registering an appeal noting the out-of-scope work, the re-evaluation upheld the APPROVE verdict with 85% confidence and directly addressed the appeal reason in the reasoning.

## How to run it

Go to GenLayer Studio at https://studio.genlayer.com and create a new file called appeal_verdict.py. Paste the contract code and set execution mode to Normal Full Consensus. Deploy with your address as owner_address.

Follow this order and wait for FINALIZED before each next step. Run get_summary first, then submit_case, then evaluate, then get_case to check the verdict, then register_appeal if you want to challenge it, then re_evaluate, then get_case again to see the final outcome.

## Resources

GenLayer Appeal Process: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/appeal-process

Optimistic Democracy: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy

GenLayer Studio: https://studio.genlayer.com

Discord: https://discord.gg/8Jm4v89VAu
