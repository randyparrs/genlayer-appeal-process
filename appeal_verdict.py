# { "Depends": "py-genlayer:test" }

import json
from genlayer import *


class AppealVerdictSystem(gl.Contract):

    owner: Address
    case_counter: u256
    case_data: DynArray[str]

    def __init__(self, owner_address: str):
        self.owner = Address(owner_address)
        self.case_counter = u256(0)

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        title = self._get(case_id, "title")
        if not title:
            return "Case not found"
        return (
            f"ID: {case_id} | "
            f"Title: {title} | "
            f"Status: {self._get(case_id, 'status')} | "
            f"Verdict: {self._get(case_id, 'verdict')} | "
            f"Confidence: {self._get(case_id, 'confidence')}% | "
            f"Appeal Round: {self._get(case_id, 'appeal_round')} | "
            f"Reasoning: {self._get(case_id, 'reasoning')}"
        )

    @gl.public.view
    def get_case_count(self) -> u256:
        return self.case_counter

    @gl.public.view
    def get_summary(self) -> str:
        return (
            f"Appeal-Aware Verdict System\n"
            f"Total Cases: {int(self.case_counter)}"
        )

    @gl.public.write
    def submit_case(self, title: str, description: str, evidence_url: str) -> str:
        case_id = str(int(self.case_counter))

        self._set(case_id, "title", title)
        self._set(case_id, "description", description[:500])
        self._set(case_id, "evidence_url", evidence_url)
        self._set(case_id, "status", "pending")
        self._set(case_id, "verdict", "")
        self._set(case_id, "confidence", "0")
        self._set(case_id, "appeal_round", "0")
        self._set(case_id, "appeal_reason", "")
        self._set(case_id, "reasoning", "")

        self.case_counter = u256(int(self.case_counter) + 1)
        return f"Case {case_id} submitted: {title}"

    @gl.public.write
    def evaluate(self, case_id: str) -> str:
        assert self._get(case_id, "status") == "pending", "Case is not pending"

        title = self._get(case_id, "title")
        description = self._get(case_id, "description")
        evidence_url = self._get(case_id, "evidence_url")

        def leader_fn():
            web_data = ""
            try:
                response = gl.nondet.web.get(evidence_url)
                raw = response.body.decode("utf-8")
                try:
                    json.loads(raw)
                    web_data = raw[:2000]
                except Exception:
                    web_data = raw[:2000]
            except Exception:
                web_data = "No evidence data available."

            prompt = f"""You are an impartial judge evaluating a case.

Case Title: {title}

Case Description:
{description}

Evidence content:
{web_data}

Evaluate the case based on the description and evidence provided.

Respond ONLY with this JSON:
{{"verdict": "APPROVE", "confidence": 80, "reasoning": "two sentences explaining the verdict"}}

verdict must be exactly APPROVE or REJECT, confidence is 0 to 100, reasoning is two sentences max.
No extra text."""

            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)

            verdict = data.get("verdict", "REJECT")
            confidence = int(data.get("confidence", 50))
            reasoning = data.get("reasoning", "")

            if verdict not in ("APPROVE", "REJECT"):
                verdict = "REJECT"
            confidence = max(0, min(100, confidence))

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if leader_data["verdict"] != validator_data["verdict"]:
                    return False
                return abs(leader_data["confidence"] - validator_data["confidence"]) <= 15
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        data = json.loads(raw)

        self._set(case_id, "status", "evaluated")
        self._set(case_id, "verdict", data["verdict"])
        self._set(case_id, "confidence", str(data["confidence"]))
        self._set(case_id, "reasoning", data["reasoning"])

        return (
            f"Case {case_id} evaluated. "
            f"Verdict: {data['verdict']} ({data['confidence']}% confidence). "
            f"{data['reasoning']}"
        )

    @gl.public.write
    def register_appeal(self, case_id: str, reason: str) -> str:
        assert self._get(case_id, "status") == "evaluated", "Case must be evaluated first"
        assert len(reason) >= 10, "Appeal reason must be at least 10 characters"

        current_round = int(self._get(case_id, "appeal_round") or "0")
        assert current_round < 3, "Maximum appeal rounds reached"

        self._set(case_id, "appeal_round", str(current_round + 1))
        self._set(case_id, "status", "appealed")
        self._set(case_id, "appeal_reason", reason[:300])

        return (
            f"Appeal registered for case {case_id}. "
            f"Round {current_round + 1}. "
            f"Call re_evaluate to have the expanded validator set reassess this case."
        )

    @gl.public.write
    def re_evaluate(self, case_id: str) -> str:
        assert self._get(case_id, "status") == "appealed", "Case must be appealed first"

        title = self._get(case_id, "title")
        description = self._get(case_id, "description")
        evidence_url = self._get(case_id, "evidence_url")
        appeal_reason = self._get(case_id, "appeal_reason")
        previous_verdict = self._get(case_id, "verdict")
        appeal_round = self._get(case_id, "appeal_round")

        def leader_fn():
            web_data = ""
            try:
                response = gl.nondet.web.get(evidence_url)
                raw = response.body.decode("utf-8")
                try:
                    json.loads(raw)
                    web_data = raw[:2000]
                except Exception:
                    web_data = raw[:2000]
            except Exception:
                web_data = "No evidence data available."

            prompt = f"""You are an impartial judge conducting an appeal re-evaluation.
This is appeal round {appeal_round}.

Case Title: {title}

Case Description:
{description}

Evidence content:
{web_data}

Previous verdict: {previous_verdict}

Reason for appeal:
{appeal_reason}

Re-evaluate the case considering the appeal reason. You may uphold or overturn the previous verdict.

Respond ONLY with this JSON:
{{"verdict": "APPROVE", "confidence": 85, "reasoning": "two sentences on the re-evaluation", "overturned": false}}

verdict is exactly APPROVE or REJECT, confidence is 0 to 100, overturned is true if this differs from the previous verdict.
No extra text."""

            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)

            verdict = data.get("verdict", "REJECT")
            confidence = int(data.get("confidence", 50))
            reasoning = data.get("reasoning", "")
            overturned = bool(data.get("overturned", False))

            if verdict not in ("APPROVE", "REJECT"):
                verdict = "REJECT"
            confidence = max(0, min(100, confidence))

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning,
                "overturned": overturned
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if leader_data["verdict"] != validator_data["verdict"]:
                    return False
                return abs(leader_data["confidence"] - validator_data["confidence"]) <= 15
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        data = json.loads(raw)

        overturned_text = "Verdict OVERTURNED" if data["overturned"] else "Verdict UPHELD"

        self._set(case_id, "status", "final")
        self._set(case_id, "verdict", data["verdict"])
        self._set(case_id, "confidence", str(data["confidence"]))
        self._set(case_id, "reasoning", data["reasoning"])

        return (
            f"Re-evaluation complete for case {case_id}. "
            f"{overturned_text}. "
            f"Final verdict: {data['verdict']} ({data['confidence']}% confidence). "
            f"{data['reasoning']}"
        )

    def _get(self, case_id: str, field: str) -> str:
        key = f"{case_id}_{field}:"
        for i in range(len(self.case_data)):
            if self.case_data[i].startswith(key):
                return self.case_data[i][len(key):]
        return ""

    def _set(self, case_id: str, field: str, value: str) -> None:
        key = f"{case_id}_{field}:"
        for i in range(len(self.case_data)):
            if self.case_data[i].startswith(key):
                self.case_data[i] = f"{key}{value}"
                return
        self.case_data.append(f"{key}{value}")
