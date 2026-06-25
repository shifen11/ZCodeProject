"""System prompt：面试教练，可按需拼入简历/题库。"""

BASE_SYSTEM_PROMPT = """你是一位资深面试教练，帮助求职者应对面试。

任务：针对面试官的问题，给出回答建议。要求：
1. 先简要点出面试官在考察什么
2. 给出 1-2 个回答方向/要点（建议用 STAR 结构：情境-任务-行动-结果）
3. 如适合，给一个简短的回答示范开头
4. 不要替求职者编造具体经历或数据，只给思路和框架

特别注意：
- 如果面试官的话只是寒暄/闲聊（如"你今天怎么样""路上堵车吗"），不要给正式回答建议，只回复"[非正式问题，闲聊即可]"。
"""

# 向后兼容别名：suggest.py / chat.py 在引入文档拼接前仍用旧名。
# Task 5/7 会把它们改为调用 build_system_prompt，届时可删除本别名。
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

_RESUME_HEADER = "====== 用户的简历 ======"
_QA_HEADER = "====== 用户的面试题库（常见问题及准备好的答案）======"
_USAGE_NOTES = """使用说明：
- 简历：回答时引用用户的真实经历，不要编造
- 题库：如果面试官的问题接近题库里的题，优先参考用户已准备的答案"""


def build_system_prompt(resume_text: str, qa_text: str) -> str:
    """在基础 prompt 上拼入简历/题库全文。

    - 无任何文档时返回 BASE_SYSTEM_PROMPT（不追加空区，避免误导）。
    - 有文档时追加对应区 + 使用说明。
    """
    has_resume = bool(resume_text.strip())
    has_qa = bool(qa_text.strip())
    if not has_resume and not has_qa:
        return BASE_SYSTEM_PROMPT

    parts = [BASE_SYSTEM_PROMPT, ""]
    if has_resume:
        parts.extend([_RESUME_HEADER, resume_text.strip(), ""])
    if has_qa:
        parts.extend([_QA_HEADER, qa_text.strip(), ""])
    parts.append(_USAGE_NOTES)
    return "\n".join(parts)
