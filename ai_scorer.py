import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

NG_WORDS = [
    "絶対稼げます", "絶対稼げる", "絶対に稼げ",
    "元取れます", "元取れる", "元が取れ",
    "必ず稼げ", "絶対儲かり", "100%稼げ",
]

COMPLIANCE_NG_PATTERNS = [
    "今すぐ決めてください", "今日中に決め", "今決めないと",
    "強制的に", "やらせます", "絶対にやってもらいます",
]


def check_ng_words(text: str) -> list[str]:
    violations = []
    for word in NG_WORDS:
        if word in text:
            violations.append(f"NGワード検出: 「{word}」")
    for phrase in COMPLIANCE_NG_PATTERNS:
        if phrase in text:
            violations.append(f"強制・圧迫表現検出: 「{phrase}」")
    return violations


def score_answer(
    category_name: str,
    customer_text: str,
    answer_text: str,
    registered_cases: list[dict],
) -> dict:
    ng_violations = check_ng_words(answer_text)

    cases_text = "\n".join(
        [f"- {c['person_name']}: {c['story_text'][:150]}..." for c in registered_cases if c.get("allowed")]
    ) or "（登録済み事例なし）"

    prompt = f"""あなたは営業トレーニングアプリのAI採点者です。

以下の営業回答を、100点満点で採点してください。

カテゴリ: {category_name}
お客様の発言: {customer_text}
営業回答: {answer_text}

評価項目：
1. 共感・承認：20点 - お客様の感情や不安に共感し、承認しているか
2. 本質の言語化：20点 - お客様の本質的な不安や課題を言語化できているか
3. 第三者トーク：20点 - 実在する事例（登録済み第三者トーク）を効果的に使えているか
4. 未来提示・行動正当化：20点 - 行動することの未来メリットや現状維持のリスクを提示できているか
5. クロージング設計：20点 - 次の行動に自然に導くクロージングができているか

合格基準：
- 80点以上
- コンプラNGがないこと

コンプラNG（自動的に不合格）：
- 「絶対稼げます」等の断定的収益保証表現
- 「元取れます」等の投資回収保証表現
- 強制・圧迫に聞こえる表現
- 登録されていない実在不明の第三者トーク

登録済み第三者事例（これ以外の実名事例はNGとなる）：
{cases_text}

出力は必ずJSON形式のみで返してください（説明文・マークダウン不要）:
{{
  "score": number,
  "passed": boolean,
  "compliance_ng": boolean,
  "compliance_reasons": [],
  "details": {{
    "empathy": number,
    "essence": number,
    "third_party_story": number,
    "future_presentation": number,
    "closing": number
  }},
  "good_points": "string",
  "improvement_points": "string",
  "suggested_answer": "string"
}}"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    result_text = message.content[0].text.strip()
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()

    result = json.loads(result_text)

    if ng_violations:
        result["compliance_ng"] = True
        result["passed"] = False
        existing = result.get("compliance_reasons", [])
        result["compliance_reasons"] = existing + ng_violations

    return result
