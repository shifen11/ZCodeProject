"""测试 system prompt 的文档拼接。"""

from app.prompts import BASE_SYSTEM_PROMPT, build_system_prompt


def test_no_documents_returns_base_prompt():
    prompt = build_system_prompt(resume_text="", qa_text="")
    assert prompt == BASE_SYSTEM_PROMPT
    # 无文档时不应出现文档区标题
    assert "用户的简历" not in prompt
    assert "面试题库" not in prompt


def test_resume_only_appended():
    prompt = build_system_prompt(resume_text="张三的简历内容", qa_text="")
    assert "张三的简历内容" in prompt
    assert "面试题库" not in prompt


def test_qa_only_appended():
    prompt = build_system_prompt(resume_text="", qa_text="常见问题及答案")
    assert "常见问题及答案" in prompt
    assert "用户的简历" not in prompt


def test_both_appended_with_usage_notes():
    prompt = build_system_prompt(resume_text="简历X", qa_text="题库Y")
    assert "简历X" in prompt
    assert "题库Y" in prompt
    assert "引用用户的真实经历" in prompt
    assert "优先参考用户已准备的答案" in prompt
