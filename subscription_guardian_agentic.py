import streamlit as st
from datetime import datetime
import json
import os
import time

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

st.set_page_config(
    page_title="Subscription Guardian",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "actions" not in st.session_state:
    st.session_state.actions = []

if "memory" not in st.session_state:
    st.session_state.memory = []

if "agent_runs" not in st.session_state:
    st.session_state.agent_runs = 0

if "last_results" not in st.session_state:
    st.session_state.last_results = []

if "last_run_time" not in st.session_state:
    st.session_state.last_run_time = None

if "completed_actions" not in st.session_state:
    st.session_state.completed_actions = set()

if "kept_items" not in st.session_state:
    st.session_state.kept_items = set()


subscriptions = [
    {
        "name": "StreamFlix",
        "amount": 14.99,
        "last_used": 187,
        "category": "Entertainment",
        "protected": False,
        "shared": False
    },
    {
        "name": "TuneWave",
        "amount": 9.99,
        "last_used": 4,
        "category": "Music Streaming",
        "protected": False,
        "shared": False
    },
    {
        "name": "MusicBox Premium",
        "amount": 11.99,
        "last_used": 40,
        "category": "Music Streaming",
        "protected": False,
        "shared": False
    },
    {
        "name": "HealthGuard Insurance",
        "amount": 89.00,
        "last_used": 10,
        "category": "Insurance",
        "protected": True,
        "shared": False
    },
    {
        "name": "CloudDrive",
        "amount": 4.99,
        "last_used": 8,
        "category": "Cloud Storage",
        "protected": False,
        "shared": True
    }
]


def money(value):
    return f"${value:,.2f}"


def save_memory(message):
    st.session_state.memory.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message
    })


def get_memory():
    return st.session_state.memory[-10:]


def detect_overlaps(items):
    categories = {}

    for item in items:
        category = item["category"]

        if category not in categories:
            categories[category] = []

        categories[category].append(item)

    overlaps = []

    for category, group in categories.items():
        if len(group) > 1:
            overlaps.append({
                "category": category,
                "subscriptions": [
                    x["name"] for x in group
                ]
            })

    return overlaps


def audit_subscription(item):
    return {
        "name": item["name"],
        "amount": item["amount"],
        "last_used": item["last_used"],
        "category": item["category"],
        "protected": item["protected"],
        "shared": item["shared"]
    }


def fallback_agent(item, overlaps):

    if item["protected"]:
        return {
            "action": "ESCALATE",
            "reason": "Protected category. Automatic cancellation is blocked.",
            "next_step": "Manual review required."
        }

    overlap_categories = [
        x["category"] for x in overlaps
    ]

    if item["last_used"] > 60 and item["amount"] <= 20:
        return {
            "action": "AUTO-CANCEL",
            "reason": "This subscription has been inactive for more than 60 days and is within the low-risk action limit.",
            "next_step": "Prepare a reversible cancellation."
        }

    if item["category"] in overlap_categories:
        return {
            "action": "ASK USER",
            "reason": "Another active subscription exists in the same category.",
            "next_step": "Ask the user before cancelling."
        }

    return {
        "action": "KEEP",
        "reason": "The subscription is currently being used and there is not enough evidence for cancellation.",
        "next_step": "Continue monitoring."
    }


def ask_ai_agent(item, overlaps, memory):

    api_key = os.getenv("OPENAI_API_KEY")

    if OpenAI is None or not api_key:
        return fallback_agent(item, overlaps), "Local safety agent"

    try:
        client = OpenAI(api_key=api_key)

        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-4.1-mini"
        )

        prompt = f"""
You are a subscription management decision engine.

Choose exactly one:
AUTO-CANCEL
ASK USER
KEEP
ESCALATE

Safety rules:
- Never automatically cancel protected subscriptions.
- AUTO-CANCEL only if protected=false, amount<=20 and last_used>60.
- If there is category overlap, prefer ASK USER.
- Insurance must be ESCALATE.
- If uncertain, ASK USER.
- Do not invent information.
- Financial actions are simulated.

Subscription:
{json.dumps(item)}

Overlaps:
{json.dumps(overlaps)}

Memory:
{json.dumps(memory)}

Return only JSON:

{{
    "action": "AUTO-CANCEL | ASK USER | KEEP | ESCALATE",
    "reason": "short reason",
    "next_step": "short next step"
}}
"""

        response = client.responses.create(
            model=model,
            input=prompt
        )

        result = json.loads(
            response.output_text
        )

        allowed = {
            "AUTO-CANCEL",
            "ASK USER",
            "KEEP",
            "ESCALATE"
        }

        if result.get("action") not in allowed:
            raise ValueError()

        return result, "AI decision engine"

    except Exception:
        return fallback_agent(
            item,
            overlaps
        ), "Local safety fallback"


def enforce_safety(item, decision):

    if item["protected"]:
        return {
            "action": "ESCALATE",
            "reason": "Safety policy blocked automatic action because this is a protected subscription.",
            "next_step": "Manual review required."
        }

    if decision["action"] == "AUTO-CANCEL":

        if item["amount"] > 20 or item["last_used"] <= 60:
            return {
                "action": "ASK USER",
                "reason": "Safety policy requires user approval.",
                "next_step": "Ask the user before taking action."
            }

    return decision


def is_completed(name):
    return name in st.session_state.completed_actions


def is_kept(name):
    return name in st.session_state.kept_items


def approve_cancellation(item):

    name = item["name"]

    if name in st.session_state.completed_actions:
        return

    st.session_state.completed_actions.add(name)

    record = {
        "subscription": name,
        "action": "USER-APPROVED CANCEL",
        "status": "SIMULATED",
        "reversible": True,
        "window": "48 hours",
        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    st.session_state.actions.append(record)

    save_memory(
        f"User approved cancellation of {name}. Reversible for 48 hours."
    )


def keep_subscription(item):

    name = item["name"]

    st.session_state.kept_items.add(name)

    save_memory(
        f"User chose to keep {name}."
    )


def run_agent():

    st.session_state.agent_runs += 1

    activity = [
        "Connecting to subscription data",
        "Auditing recurring charges",
        "Checking recent usage",
        "Detecting duplicate categories",
        "Evaluating financial risk",
        "Running safety policies",
        "Planning recommended actions",
        "Updating agent memory"
    ]

    box = st.empty()

    for step in activity:
        box.info(
            f"🤖 {step}..."
        )
        time.sleep(0.25)

    box.empty()

    overlaps = detect_overlaps(
        subscriptions
    )

    results = []

    for item in subscriptions:

        audited = audit_subscription(item)

        decision, source = ask_ai_agent(
            audited,
            overlaps,
            get_memory()
        )

        decision = enforce_safety(
            audited,
            decision
        )

        results.append({
            "item": audited,
            "decision": decision,
            "source": source
        })

        save_memory(
            f"Analyzed {item['name']} → {decision['action']}"
        )

    st.session_state.last_results = results

    st.session_state.last_run_time = (
        datetime.now().strftime(
            "%d %b %Y, %H:%M:%S"
        )
    )


st.markdown(
    """
    <style>
    .main-title {
        font-size: 40px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #777;
        font-size: 17px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown(
    '<div class="main-title">🤖 Subscription Guardian</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Your autonomous recurring-spend assistant</div>',
    unsafe_allow_html=True
)


total = sum(
    x["amount"] for x in subscriptions
)

auto_candidates = [
    x for x in subscriptions
    if not x["protected"]
    and x["amount"] <= 20
    and x["last_used"] > 60
]

monthly_savings = sum(
    x["amount"] for x in auto_candidates
)


c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Monthly recurring spend",
        money(total)
    )

with c2:
    st.metric(
        "Potential monthly savings",
        money(monthly_savings)
    )

with c3:
    st.metric(
        "Subscriptions monitored",
        len(subscriptions)
    )

with c4:
    st.metric(
        "Agent runs",
        st.session_state.agent_runs
    )


st.divider()


left, right = st.columns(
    [2.2, 1]
)


with left:

    st.subheader(
        "⚡ Agent Command Center"
    )

    if st.session_state.last_run_time:
        st.caption(
            f"Last scan: {st.session_state.last_run_time}"
        )

    if st.button(
        "▶ Run Guardian Agent",
        type="primary",
        use_container_width=True
    ):
        run_agent()

        st.success(
            "Guardian Agent completed its review."
        )

    st.write("")

    if st.session_state.last_results:

        st.subheader(
            "Agent recommendations"
        )

        for index, result in enumerate(
            st.session_state.last_results
        ):

            item = result["item"]
            decision = result["decision"]
            name = item["name"]

            completed = is_completed(name)
            kept = is_kept(name)

            if completed:
                icon = "🟢"
                displayed_action = "COMPLETED"

            elif kept:
                icon = "🔵"
                displayed_action = "KEEP"

            elif decision["action"] == "AUTO-CANCEL":
                icon = "🟢"
                displayed_action = "AUTO-CANCEL"

            elif decision["action"] == "ASK USER":
                icon = "🟡"
                displayed_action = "ASK USER"

            elif decision["action"] == "ESCALATE":
                icon = "🔴"
                displayed_action = "ESCALATE"

            else:
                icon = "🔵"
                displayed_action = "KEEP"


            with st.container(
                border=True
            ):

                a, b, c = st.columns(
                    [2.4, 1.2, 1.4]
                )

                with a:
                    st.markdown(
                        f"### {icon} {name}"
                    )

                    st.caption(
                        f"{item['category']} · Used {item['last_used']} days ago"
                    )

                with b:
                    st.write(
                        f"**{money(item['amount'])}**"
                    )

                    st.caption(
                        "per month"
                    )

                with c:
                    st.write(
                        f"**{displayed_action}**"
                    )


                if completed:

                    st.success(
                        "Cancellation completed in simulation. Reversible for 48 hours."
                    )

                elif kept:

                    st.info(
                        "User chose to keep this subscription."
                    )

                else:

                    st.write(
                        decision["reason"]
                    )


                if (
                    decision["action"] == "ASK USER"
                    and not completed
                    and not kept
                ):

                    x, y = st.columns(2)

                    with x:

                        if st.button(
                            "Keep",
                            key=f"keep_{index}_{name}"
                        ):

                            keep_subscription(item)

                            st.rerun()


                    with y:

                        if st.button(
                            "Approve cancellation",
                            key=f"approve_{index}_{name}"
                        ):

                            approve_cancellation(item)

                            st.rerun()


                elif decision["action"] == "AUTO-CANCEL":

                    if completed:

                        st.success(
                            "Action completed."
                        )

                    else:

                        st.success(
                            "Autonomous action ready. Reversible for 48 hours."
                        )


                elif decision["action"] == "ESCALATE":

                    st.error(
                        "Protected subscription — manual review required."
                    )


                elif decision["action"] == "KEEP":

                    st.info(
                        "No action required. Agent will continue monitoring."
                    )


with right:

    st.subheader(
        "🔔 Action Center"
    )

    pending = []

    autonomous = []

    escalated = []

    completed = []


    if st.session_state.last_results:

        for result in st.session_state.last_results:

            item = result["item"]
            decision = result["decision"]

            if is_completed(item["name"]):
                completed.append(item)

            elif decision["action"] == "ASK USER":
                pending.append(item)

            elif decision["action"] == "AUTO-CANCEL":
                autonomous.append(item)

            elif decision["action"] == "ESCALATE":
                escalated.append(item)


    if pending:

        st.warning(
            f"{len(pending)} decision(s) need your approval."
        )

    else:

        st.success(
            "No pending approvals."
        )


    if autonomous:

        st.info(
            f"{len(autonomous)} low-risk action(s) ready."
        )


    if completed:

        st.success(
            f"{len(completed)} action(s) completed."
        )


    if escalated:

        st.error(
            f"{len(escalated)} protected subscription(s) escalated."
        )


    st.write("")

    st.subheader(
        "🔄 Overlap detected"
    )

    overlaps = detect_overlaps(
        subscriptions
    )

    if overlaps:

        for overlap in overlaps:

            st.warning(
                f"{overlap['category']}: "
                + " + ".join(
                    overlap["subscriptions"]
                )
            )

    else:

        st.success(
            "No overlaps found."
        )


st.divider()


st.subheader(
    "📡 Live Agent Activity"
)


if st.session_state.last_results:

    for result in st.session_state.last_results:

        item = result["item"]
        decision = result["decision"]
        name = item["name"]

        if is_completed(name):

            status = "ACTION COMPLETED"

        elif is_kept(name):

            status = "USER CHOSE KEEP"

        elif decision["action"] == "AUTO-CANCEL":

            status = "ACTION READY"

        elif decision["action"] == "ASK USER":

            status = "WAITING FOR USER"

        elif decision["action"] == "ESCALATE":

            status = "ESCALATED"

        else:

            status = "MONITORING"


        st.write(
            f"**{datetime.now().strftime('%H:%M:%S')}** "
            f"→ {name} → **{status}**"
        )

else:

    st.caption(
        "Run the Guardian Agent to see its execution activity."
    )


st.divider()


st.subheader(
    "🛡️ Decision Safety"
)


g1, g2, g3, g4 = st.columns(4)


with g1:

    st.metric(
        "Protected categories",
        len([
            x for x in subscriptions
            if x["protected"]
        ])
    )


with g2:

    st.metric(
        "Low-risk candidates",
        len(auto_candidates)
    )


with g3:

    st.metric(
        "Approved actions",
        len([
            x for x in st.session_state.actions
            if x["action"] == "USER-APPROVED CANCEL"
        ])
    )


with g4:

    st.metric(
        "Reversible actions",
        len([
            x for x in st.session_state.actions
            if x["reversible"]
        ])
    )


st.divider()


with st.expander(
    "🧠 View agent memory"
):

    if st.session_state.memory:

        for memory in reversed(
            st.session_state.memory[-10:]
        ):

            st.write(
                f"**{memory['time']}** — {memory['message']}"
            )

    else:

        st.caption(
            "The agent has no memory yet."
        )


with st.expander(
    "📋 View audit log"
):

    if st.session_state.actions:

        for action in reversed(
            st.session_state.actions
        ):

            st.write(
                f"**{action['subscription']}** → "
                f"{action['action']} | "
                f"{action['status']} | "
                f"Reversible: {action['reversible']} | "
                f"{action['time']}"
            )

    else:

        st.caption(
            "No actions have been recorded."
        )


with st.expander(
    "⚙️ How the agent works"
):

    st.write(
        "The Guardian Agent observes subscription data, analyzes usage and cost, detects overlaps, evaluates risk, applies safety policies, decides whether to act or ask the user, and stores the result in memory."
    )

    st.write(
        "The safety layer can override an unsafe AI decision."
    )

    st.write(
        "If an AI API is unavailable, the local decision engine keeps the prototype functional."
    )


st.caption(
    "Prototype environment · Financial actions are simulated and reversible."
)