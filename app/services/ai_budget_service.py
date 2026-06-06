from app.schemas.ai_copilot import BudgetCheckResult


class AiBudgetService:
    def check_budget(self, session_data: dict, estimated_tokens: int) -> BudgetCheckResult:
        total = session_data["token_budget_total"]
        used = session_data["tokens_used_input"] + session_data["tokens_used_output"]
        remaining = max(0, total - used)
        allowed = estimated_tokens <= remaining

        return BudgetCheckResult(
            allowed=allowed,
            remaining=remaining,
            total=total,
            used=used,
        )

    def estimate_input_tokens(self, text: str) -> int:
        return len(text) // 4 + 1
