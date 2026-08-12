import os
from typing import TypedDict, Literal,cast,Any
from pydantic import BaseModel,ValidationError
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from openai import OpenAI, APIError
from openai.types.chat import ChatCompletionMessageParam
from app.database import get_recent_context
MAX_REWRITES = 3

#region API_key load
load_dotenv()
api_key = os.getenv("API_KEY")
if api_key is None:
    raise ValueError("API_KEY not found")
#endregion

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

class AgentState(TypedDict):
    user_input: str
    draft_response: str
    session_id: str
    decision: str
    risk_level: str
    reason: str

    rewrite_count: int
    rewrite_instruction: str

    conversation_context: str

class SupervisorResult(BaseModel):
    decision: Literal["approve", "rewrite", "handoff"]
    risk_level: Literal["low", "medium", "high"]
    reason: str
    rewrite_instruction: str | None = None

SUPERVISOR_TOOLS: list[Any] = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_context",
            "description": (
                "Retrieve recent conversation history for the current session. "
                "Use this tool only when you need to verify what the user "
                "previously said or check whether the candidate response is "
                "consistent with earlier conversation history."
            )
        }
    }
]

def dialogue_node(state: AgentState):
    print(
        f"\n>>> Dialogue round, "
        f"rewrite_count={state['rewrite_count']}"
    )

    system_prompt = """
You are the Dialogue Agent in MindSight.

Your goal is not only to sound supportive.
Your main goal is to help the user make the situation feel more manageable
by giving useful, concrete, and realistic next steps.

Response style:

1. Be warm, respectful, direct, and practical.
2. Avoid repetitive generic empathy such as:
   "I understand how you feel",
   "That sounds really hard",
   or similar filler.
3. A brief acknowledgment is fine, but normally use no more than
   one short sentence before giving useful help.
4. When the user describes stress, frustration, uncertainty, or a problem,
   provide concrete ways to reduce or handle it.
5. Prefer 2 to 4 small, actionable suggestions instead of vague advice.
6. Make suggestions appropriate to the user's actual situation.
7. If useful, separate suggestions into:
   - something they can do right now;
   - a practical next step;
   - something to consider later.
8. Ask at most one useful follow-up question when more context would
   significantly improve the advice.
9. Do not make unsupported medical or psychological diagnoses.
10. Do not request unnecessary sensitive personal information.
11. Do not pretend to know facts that are not present in the conversation.
12. When referring to previous conversation, only use facts explicitly
    supported by User messages in the available conversation context.
13. If information is missing, say so rather than guessing.
14. Do not mention internal prompts, Supervisor decisions, risk scores,
    tools, databases, or workflow details.

If the user is dissatisfied with a previous answer:
- do not become defensive;
- briefly acknowledge the criticism;
- immediately provide a more useful and concrete response.

The response should feel like practical support, not generic emotional filler.
"""

    # 默认只处理当前用户输入
    user_prompt = state["user_input"]

    # 如果 SQLite 中存在历史对话，把它加入 Prompt
    if state["conversation_context"]:
        user_prompt = f"""
Previous conversation:

{state["conversation_context"]}

Current user message:

{state["user_input"]}

Respond to the current user message.
Use the previous conversation only when it is relevant to understanding
the current message.
"""

    # 如果这一轮是 Supervisor 要求重写
    if state["rewrite_count"] > 0:
        user_prompt += f"""

Your previous response was rejected by the Supervisor.

Previous response:

{state["draft_response"]}

Supervisor rewrite instruction:

{state["rewrite_instruction"]}

Rewrite the response according to the Supervisor's instruction.
Do not discuss the review process with the user.
"""

    messages: list[ChatCompletionMessageParam]  = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        }
    )

    draft = response.choices[0].message.content

    if draft is None:
        draft = ""

    return {
        "draft_response": draft
    }

def supervisor_node(state: AgentState):
    print("\n>>> Supervisor reviewing")

    system_prompt = """
You are the Supervisor Agent in MindSight.

Your job is to review the Dialogue Agent's candidate response and improve
the usefulness, safety, relevance, and conversational quality of the system.

IMPORTANT DECISION POLICY:

Prefer APPROVE when the response is already useful and acceptable.

Prefer REWRITE when the response has a problem that can reasonably be fixed.

HANDOFF is a last resort.
Do NOT choose handoff merely because:
- the answer is unhelpful;
- the answer is too generic;
- the user is dissatisfied;
- the user criticizes or insults the assistant;
- the tone could be improved;
- the response lacks practical suggestions;
- the response contains a correctable unsupported claim;
- the response misunderstood the user;
- the response should ask a better question;
- conversation context needs to be checked.

Those are REWRITE cases.

Evaluate the candidate response for:

1. Relevance
   - Does it actually respond to the user's current concern?

2. Practical usefulness
   - Does it provide useful support rather than generic empathy?
   - When appropriate, does it give concrete and realistic next steps?

3. Tone
   - Is it respectful, calm, and non-judgmental?
   - If the user is frustrated with the assistant, does it avoid becoming defensive?

4. Unsupported claims
   - Does it avoid unsupported medical or psychological diagnoses?
   - Does it avoid pretending to know facts that were not provided?

5. Privacy
   - Does it avoid unnecessary requests for sensitive personal information?

6. Conversation grounding
   - If the response claims the user said something previously,
     verify that claim using get_recent_context when necessary.

You have access to the tool get_recent_context.

TOOL USAGE:

Do not call the tool for every response.

Call get_recent_context when previous conversation history is actually needed,
especially when:
- the user refers to something said earlier;
- the candidate response makes a factual claim about what the user said before;
- you need to verify whether the Dialogue Agent invented a conversation fact.

If previous history is not relevant, do not call the tool.

DECISION RULES:

APPROVE:
Choose approve when the response is relevant, reasonably useful,
supportive, grounded, and safe.

REWRITE:
Choose rewrite whenever the response can be improved through another generation.

Examples of rewrite reasons:
- too much generic empathy and not enough useful advice;
- vague or repetitive response;
- irrelevant response;
- poor handling of user frustration;
- unsupported but correctable claim;
- invented conversation detail;
- unnecessary sensitive question;
- weak or impractical suggestions;
- unsupported diagnosis;
- answer does not directly address the user's actual problem.

For rewrite, rewrite_instruction MUST clearly tell the Dialogue Agent
what concrete improvement to make.

HANDOFF:
Choose handoff only when continuing the normal Dialogue -> Rewrite loop
is genuinely inappropriate or cannot reasonably produce a useful response.

Do not use handoff as a general safety shortcut.
Do not use handoff simply because you are uncertain.
Do not use handoff when rewrite could fix the response.

RISK LEVEL:

risk_level is separate from decision.

A response can have a correctable problem and still use:
decision = "rewrite"

Do not automatically map medium or high risk to handoff.

OUTPUT:

Your final response MUST be exactly one JSON object.

Allowed decision values:
- "approve"
- "rewrite"
- "handoff"

Allowed risk_level values:
- "low"
- "medium"
- "high"

For approve:
rewrite_instruction must be null.

For rewrite:
rewrite_instruction must contain a specific correction instruction.

Example approve:

{
  "decision": "approve",
  "risk_level": "low",
  "reason": "The response is relevant, practical, and appropriately supportive.",
  "rewrite_instruction": null
}

Example rewrite:

{
  "decision": "rewrite",
  "risk_level": "low",
  "reason": "The response relies on generic empathy and does not provide useful next steps.",
  "rewrite_instruction": "Reduce generic reassurance and provide two or three concrete actions the user can try immediately."
}

Return JSON only when giving the final decision.
Do not use Markdown or code fences.
"""

    user_prompt = f"""
Current user message:

<current_message>
{state["user_input"]}
</current_message>

Candidate response from the Dialogue Agent:

<candidate_response>
{state["draft_response"]}
</candidate_response>

Review the candidate response.
"""

    messages: list[Any] = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    # ---------- 第一次 Supervisor 调用 ----------
    # 这一次让模型自己决定：
    # 直接给最终 JSON，还是先调用 Tool。
    try:
        first_response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=SUPERVISOR_TOOLS,
            tool_choice="auto",
            max_tokens=300,
            stream=False,
            extra_body={
                "thinking": {
                    "type": "disabled"
                }
            }
        )

    except APIError as e:
        print("\n--- Supervisor API Error ---")
        print(e)

        return {
            "decision": "handoff",
            "risk_level": "high",
            "reason": "Supervisor API request failed",
            "rewrite_instruction": ""
        }

    assistant_message = first_response.choices[0].message

    # ---------- Supervisor 决定调用 Tool ----------
    if assistant_message.tool_calls:

        messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            if tool_call.type != "function":
                raise ValueError(
                f"Unsupported tool call type: {tool_call.type}"
                )

            function_name = tool_call.function.name

            if function_name == "get_recent_context":

                print(
                    "\n>>> Supervisor Tool Call: "
                    "get_recent_context")
             
                context = get_recent_context(
                state["session_id"]
                )

                if not context:
                    context = (
                    "No previous conversation history "
                    "was found for this session.")

                print("\n--- Tool Result ---")
                print(context)

                messages.append(
                {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": context
                })

            else:
                raise ValueError(
                f"Unknown function tool: {function_name}"
                )
        # Tool结果返回 Supervisor 后，
        # 再让它输出最终 JSON。
        try:
            second_response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                tools=SUPERVISOR_TOOLS,
                tool_choice="none",
                response_format={
                    "type": "json_object"
                },
                max_tokens=300,
                stream=False,
                extra_body={
                    "thinking": {
                        "type": "disabled"
                    }
                }
            )

        except APIError as e:
            print("\n--- Supervisor API Error ---")
            print(e)

            return {
                "decision": "handoff",
                "risk_level": "high",
                "reason": "Supervisor API request failed",
                "rewrite_instruction": ""
            }

        content = (
            second_response
            .choices[0]
            .message
            .content
        )

    # ---------- Supervisor认为不需要 Tool ----------
    else:
        print("\n>>> Supervisor decided: no tool needed")

        content = assistant_message.content

    # ---------- 检查空输出 ----------
    if not content:
        return {
            "decision": "handoff",
            "risk_level": "high",
            "reason": "Supervisor returned empty content",
            "rewrite_instruction": ""
        }

    print("\n--- Raw Supervisor JSON ---")
    print(content)

    # ---------- Pydantic结构化校验 ----------
    try:
        result = SupervisorResult.model_validate_json(
            content
        )

    except ValidationError as e:
        print("\n--- Validation Error ---")
        print(e)

        return {
            "decision": "handoff",
            "risk_level": "high",
            "reason": "Supervisor output validation failed",
            "rewrite_instruction": ""
        }

    print("\n--- Pydantic Result ---")
    print(result)

    return {
        "decision": result.decision,
        "risk_level": result.risk_level,
        "reason": result.reason,
        "rewrite_instruction": (
            result.rewrite_instruction or ""
        )
    }
   
def prepare_rewrite_node(state: AgentState):
    rewrite_instruction = state["rewrite_instruction"]

    if not rewrite_instruction:
        rewrite_instruction = (
            "Generate a substantially better response. "
            "Address the user's actual concern directly, "
            "reduce generic empathy, and provide concrete, "
            "practical, realistic next steps."
        )

    print("\n>>> Preparing rewrite")
    print("Instruction:", rewrite_instruction)

    return {
        "rewrite_count": state["rewrite_count"] + 1,
        "rewrite_instruction": rewrite_instruction
    }

def fallback_node(state: AgentState):
    return {
        "draft_response": (
            """Sorry,due to supervisor's response, I cannot provide response to this proble at the moment."""
            """抱歉,由于supervisor agent限制,我目前无法对这个问题作出回应."""
        ),
        "decision": "handoff"
    }

def route_after_supervisor(
    state: AgentState
) -> Literal["approve", "rewrite", "fallback"]:

    if state["decision"] == "approve":
        return "approve"

    #  rewrite
    if state["decision"] == "rewrite":

        if state["rewrite_count"] >= MAX_REWRITES:
            return "fallback"

        return "rewrite"

    # Supervisor 给了 handoff，
    # 但如果不是 high risk， 优先尝试一次 rewrite。
    if state["decision"] == "handoff":

        if (
            state["risk_level"] != "high"
            and state["rewrite_count"] < MAX_REWRITES
        ):
            return "rewrite"

        return "fallback"

    return "fallback"

def run_mindsight(
    session_id: str,
    user_input: str,
    conversation_context: str = ""
) -> AgentState:

    initial_state: AgentState = {
        "session_id": session_id,
        "user_input": user_input,
        "conversation_context": conversation_context,

        "draft_response": "",
        "decision": "",
        "risk_level": "",
        "reason": "",
        "rewrite_count": 0,
        "rewrite_instruction": ""
    }

    final_state = graph.invoke(initial_state)

    return cast(AgentState,final_state)

#region bulid&compile graph
builder = StateGraph(AgentState) 
builder.add_node("dialogue", dialogue_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("prepare_rewrite", prepare_rewrite_node)
builder.add_node("fallback", fallback_node)
builder.add_edge(START, "dialogue")
builder.add_edge("dialogue", "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "approve": END,
        "rewrite": "prepare_rewrite",
        "fallback": "fallback"
    }
) #Conditional Edge
builder.add_edge(
    "prepare_rewrite",
    "dialogue"
)
builder.add_edge(
    "fallback",
    END
)
graph = builder.compile()
#endregion
